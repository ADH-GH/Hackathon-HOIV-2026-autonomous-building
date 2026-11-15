"""Home Assistant cached-state observation only; never invokes a service or control.

Bridge report freshness is not a trustworthy physical observation timestamp.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from urllib.parse import urlsplit, quote

from .adapters.http_readonly import Reader as HTTPReader, decode, finite
from .decisions import Decision
from .telemetry import TelemetryError, alias, timestamp, utc

METRICS={'valve_state','active_watering','remaining_open_seconds','battery_percent','flow_l_min','cumulative_volume_l'}


def entity_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9_]*\.[a-z0-9_]+',value) or len(value)>255:
        raise TelemetryError('invalid Home Assistant entity identifier')
    return value


class Reader:
    def __init__(self, base_url, *, live_authorized=False, token_env=None, attempts=3, timeout=5):
        parsed=urlsplit(base_url)
        if parsed.path not in ('','/'):
            raise TelemetryError('Home Assistant requires an origin URL without a path')
        self.base=base_url.rstrip('/')
        self.loopback=parsed.hostname in {'127.0.0.1','::1'}
        # Do not send ambient real credentials to synthetic loopback servers.
        self.token_env=token_env or (None if self.loopback else 'HA_TOKEN')
        self.authorized,self.attempts,self.timeout=live_authorized,attempts,timeout
        HTTPReader(self.base+'/api/states',authorized=live_authorized,token_env=self.token_env,
                   attempts=attempts,timeout=timeout,media_type='application/json')
        self.last_transport={'state':'not_read','attempts':0}

    def _get(self, path):
        reader=HTTPReader(self.base+path,authorized=self.authorized,token_env=self.token_env,
                          attempts=self.attempts,timeout=self.timeout,media_type='application/json')
        self.last_transport={'state':'unavailable','attempts':None,'reason':'read_failed_before_transport_report'}
        raw,self.last_transport=reader.read()
        if raw is None:
            raise TelemetryError('Home Assistant read unavailable; no state inferred')
        self.last_transport['payload_sha256']=hashlib.sha256(raw).hexdigest()
        try:
            return decode(raw)
        except TelemetryError:
            self.last_transport['state']='invalid_payload'
            raise

    def state(self, entity):
        entity=entity_id(entity)
        row=self._get('/api/states/'+quote(entity,safe=''))
        if not isinstance(row,dict) or row.get('entity_id')!=entity:
            raise TelemetryError('state identity mismatch')
        return row

    def states(self):
        rows=self._get('/api/states')
        if not isinstance(rows,list) or len(rows)>10000:
            raise TelemetryError('expected a bounded state list')
        seen=set()
        for row in rows:
            if not isinstance(row,dict): raise TelemetryError('state objects required')
            key=entity_id(row.get('entity_id'))
            if key in seen: raise TelemetryError('duplicate state identity')
            seen.add(key)
        return rows


def normalize(state, *, asset, metric, now, max_age=180):
    alias(asset)
    if metric not in METRICS or not finite(max_age) or max_age<=0:
        raise TelemetryError('supported metric and positive freshness policy required')
    if not isinstance(state,dict): raise TelemetryError('state object required')
    entity=entity_id(state.get('entity_id'))
    stamp=state.get('last_reported')
    try: payload_hash=hashlib.sha256(json.dumps(state,sort_keys=True,allow_nan=False).encode()).hexdigest()
    except (ValueError,TypeError,OverflowError) as exc: raise TelemetryError('state must contain finite JSON values') from exc
    record=dict(schema_version=1,source='gardena_ha',asset_id=asset,entity_id=entity,metric=metric,
        received_utc=utc(now),source_timestamp=stamp,last_changed=state.get('last_changed'),
        last_updated=state.get('last_updated'),value=None,quality='unknown',
        freshness_basis='home_assistant_report',physical_state_verified=False,
        payload_sha256=payload_hash)
    try:
        if stamp is None: return dict(record,reason='no report timestamp')
        observed=timestamp(stamp); age=(now-observed).total_seconds()
        if age<0: return dict(record,quality='invalid',reason='future report timestamp')
        if age>max_age: return dict(record,quality='stale',reason='report too old')
        raw=state.get('state'); attributes=state.get('attributes',{})
        if not isinstance(attributes,dict): raise ValueError('invalid attributes')
        if raw in (None,'unknown','unavailable'): return dict(record,reason='entity unavailable or unknown')
        unit=attributes.get('unit_of_measurement')
        if metric=='valve_state':
            values={'on':'open','off':'closed','open':'open','closed':'closed'}
            if raw not in values: return dict(record,reason='valve state not settled')
            value=values[raw]
        elif metric=='active_watering':
            if raw not in ('on','off','true','false'): raise ValueError('invalid watering state')
            value=raw in ('on','true')
        else:
            if isinstance(raw,bool): raise ValueError('Boolean is not a numeric reading')
            value=float(raw)
            if metric=='cumulative_volume_l' and attributes.get('state_class') not in {'total','total_increasing'}:
                return dict(record,reason='cumulative semantics not declared by entity metadata')
            factors={'flow_l_min':{'L/min':1,'L/h':1/60,'L/s':60,'m³/h':1000/60,'m3/h':1000/60},
                     'cumulative_volume_l':{'L':1,'m³':1000,'m3':1000},
                     'battery_percent':{'%':1},'remaining_open_seconds':{'s':1,'min':60}}
            if unit not in factors[metric] or not math.isfinite(value) or value<0: raise ValueError('invalid measurement')
            value*=factors[metric][unit]
            if not math.isfinite(value) or metric=='battery_percent' and value>100: raise ValueError('range')
        return dict(record,value=value,quality='valid')
    except (ValueError,TypeError,OverflowError,TelemetryError):
        return dict(record,quality='invalid',reason='invalid timestamp or measurement')


class CumulativeFlow:
    """Averaged rate only from consecutive qualified independently reported volumes."""
    def __init__(self,max_interval_seconds):
        self.previous=None;self.limit=max_interval_seconds

    def rate(self,row):
        result=dict(row,metric='flow_l_min',value=None,quality='unknown',reason='counter baseline required',flow_basis='cumulative_delta')
        if row['quality']!='valid': self.previous=None;return result
        now=timestamp(row['source_timestamp']); previous=self.previous
        self.previous=row
        if previous is None:return result
        seconds=(now-timestamp(previous['source_timestamp'])).total_seconds()
        if seconds==0 and row['value']==previous['value']:
            return dict(result,reason='duplicate counter report; no new interval')
        if seconds<=0:
            self.previous=None;return dict(result,quality='invalid',reason='out-of-order or conflicting counter time')
        if seconds>self.limit:return dict(result,reason='counter interval exceeds configured coverage limit')
        delta=row['value']-previous['value']
        if delta<0:return dict(result,quality='invalid',reason='counter reset; no negative consumption inferred')
        value=delta*60/seconds
        if not finite(value):return dict(result,quality='invalid',reason='rate overflow')
        return dict(result,value=value,quality='valid',reason='qualified cumulative interval',
                    interval_start_utc=previous['source_timestamp'],interval_end_utc=row['source_timestamp'],
                    payload_sha256=hashlib.sha256((previous['payload_sha256']+row['payload_sha256']).encode()).hexdigest())


def detect(records, config):
    """Qualified reported-state discrepancies, not proof of a leak or actual flow truth."""
    for name in ('flow_tolerance_l_min','persistence_seconds','settle_seconds','max_skew_seconds'):
        if not finite(config.get(name)) or config[name]<0: raise TelemetryError('explicit nonnegative flow monitoring policy required')
    if config.get('hydraulic_scope_confirmed') is not True:return []
    max_age=config.get('max_age_seconds',180); max_gap=config.get('max_gap_seconds',max_age)
    if not finite(max_age) or not finite(max_gap) or min(max_age,max_gap)<=0: raise TelemetryError('positive freshness/coverage policy required')
    frames=defaultdict(list)
    for r in records:
        asset=alias(r.get('asset_id')); at=timestamp(r.get('received_utc'))
        if r.get('metric') not in METRICS or r.get('quality') not in {'valid','unknown','stale','invalid'}: raise TelemetryError('invalid normalized record')
        env=r.get('environment',config.get('environment','imported_unknown'))
        if env not in {'synthetic_fixture','external_shadow','imported_unknown'}: raise TelemetryError('invalid source environment')
        frames[(asset,env,at)].append(r)
    states={};decisions=[]
    for (asset,env,at), frame in sorted(frames.items(),key=lambda pair:(pair[0][2],pair[0][0],pair[0][1])):
        st=states.setdefault((asset,env),dict(latest={},changed=None,valve=None,since=None,kind=None,emitted=False,pair=None,at=None))
        if st['at'] is not None and (at-st['at']).total_seconds()>max_gap:
            st.update(latest={},changed=None,valve=None,since=None,kind=None,emitted=False,pair=None)
        st['at']=at
        metrics=set()
        for r in frame:
            if r['metric'] in metrics: raise TelemetryError('duplicate metric in one asset snapshot')
            metrics.add(r['metric']);st['latest'][r['metric']]=r
        valve,flow=st['latest'].get('valve_state'),st['latest'].get('flow_l_min')
        if not valve or valve['quality']!='valid':
            st.update(since=None,pair=None,changed=None,valve=None,emitted=False);continue
        valve_time=timestamp(valve['source_timestamp'])
        if not 0<=(at-valve_time).total_seconds()<=max_age:
            st.update(since=None,pair=None,changed=None,valve=None,emitted=False);continue
        if valve['value'] not in {'open','closed'}: raise TelemetryError('invalid qualified valve value')
        if valve['value']!=st['valve']:
            st.update(valve=valve['value'],changed=at,since=None,emitted=False,pair=None)
        if not flow or flow['quality']!='valid':
            st.update(since=None,pair=None,emitted=False);continue
        if not finite(flow['value']) or flow['value']<0: raise TelemetryError('invalid qualified flow value')
        stamps=[valve_time,timestamp(flow['source_timestamp'])]
        if any((at-t).total_seconds()<0 or (at-t).total_seconds()>max_age for t in stamps) or abs((stamps[0]-stamps[1]).total_seconds())>config['max_skew_seconds']:
            st.update(since=None,pair=None,emitted=False);continue
        progress=min(stamps)
        if st['pair'] is not None and progress<st['pair']:
            st.update(since=None,pair=None,emitted=False);continue
        if st['pair'] is not None and progress==st['pair']:continue # cached polls do not establish persistence
        if st['pair'] is not None and (progress-st['pair']).total_seconds()>max_gap:
            st.update(since=None,changed=at,emitted=False)
        st['pair']=progress
        kind='closed_with_flow' if valve['value']=='closed' and flow['value']>config['flow_tolerance_l_min'] else 'open_without_flow' if valve['value']=='open' and flow['value']<=config['flow_tolerance_l_min'] else None
        interval_start=timestamp(flow['interval_start_utc']) if flow.get('flow_basis')=='cumulative_delta' and flow.get('interval_start_utc') else None
        if kind is None or (at-st['changed']).total_seconds()<config['settle_seconds'] or interval_start is not None and (interval_start-st['changed']).total_seconds()<config['settle_seconds']:
            st.update(since=None,kind=kind,emitted=False);continue
        if kind!=st['kind']:st.update(since=None,kind=kind,emitted=False)
        st['since']=st['since'] or progress
        if not st['emitted'] and (progress-st['since']).total_seconds()>=config['persistence_seconds']:
            st['emitted']=True
            decisions.append(Decision(timestamp_utc=at,affected_assets=[asset],issue_type='irrigation_state_conflict',action='flag_anomaly',priority='medium',
                episode_id=f'irrigation_ha:{asset}:{kind}:{utc(st["since"])}',
                reason=f'Reported valve/independently mapped flow discrepancy ({kind}). Possible stale state, drainage, supply interruption, obstruction or mapping error; not proof of a leak or its location.',
                evidence=[f'HA entity sha256:{hashlib.sha256(r["entity_id"].encode()).hexdigest()} report:{r["source_timestamp"]} payload:{r["payload_sha256"]}' for r in (valve,flow)],
                extra=dict(source='gardena_ha',environment=env,shadow_only=True,physical_state_verified=False,flow_discrepancy=kind)).finalize())
    return decisions
