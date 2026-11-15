"""Deterministic read-only intents. Every response uses the recorded assessment."""
import json
from .telemetry import TelemetryError, fingerprint

QUESTIONS={
 'status':'What is the last known state of my irrigation controller?',
 'watering':'Is it currently watering?',
 'observation':'When was the most recent valid observation?',
 'battery':'How much battery is left?',
 'duration':'Has watering exceeded its configured duration?',
 'warnings':'Are there any monitoring warnings?',
 'connection':'Did the Bluetooth connection drop?',
 'evidence':'What evidence supports the current warning?',
 'flow':'Can you verify that water is actually flowing?',
 'consumption':'Has the system measured any water loss?',
 'control':'Can you stop or start watering?'}


def answers(view):
    r=view['assessment'];states=[]
    for d in view['devices']:
        # Deliberately omit aliases, model identifiers, raw paths and transport IDs
        # from tool responses that might be sent to an opted-in voice service.
        states.append(dict(observed_at_utc=d['observed_at_utc'],quality=d['quality'],connection_at_observation=d['connection_state'],
            current_valve_at_cutoff=d['current_valve_state'],reported_valve_at_observation=d['valve_state'],
            reported_active_watering=d['active_watering'],reported_battery_percent=d['battery_percent'],
            last_usable_observation_utc=d['last_usable_valve_timestamp'],source_mode=d['source_mode']))
    findings=[dict(finding_id=d['event_id'],timestamp_utc=d['timestamp_utc'],issue_type=d['issue_type'],reason=d['reason'],
                   observation_hashes=[e.rsplit('sha256:',1)[-1] for e in d['evidence'] if 'sha256:' in e]) for d in r['decisions']]
    common=dict(assessment_cutoff_utc=r['as_of_utc'],verification_status=r['verification_status'],
                source_modes=r['source_modes'],static_report=True,operational_outcome='not_measured')
    disclaimer='Static report, not a live reading. Values describe reports at the stated UTC timestamps; stale/disconnected current state is unknown.'
    result={
      'status':dict(answer=disclaimer,observations=states),
      'watering':dict(answer=disclaimer+' Reported watering activity does not verify water flow.',observations=states),
      'observation':dict(answer='Last usable observation is historical; see quality and assessment cutoff.',observations=states),
      'battery':dict(answer='Battery percentages are reported at observation time, not current live measurements.',observations=states),
      'duration':dict(answer='Duration uses qualifying observations only; gaps do not establish continued watering.',watering_limit_seconds=r['monitoring_policy']['watering_limit_seconds'],findings=[f for f in findings if f['issue_type']=='irrigation_duration']),
      'warnings':dict(answer='Recorded monitoring findings, not verified equipment faults.',findings=findings,qualification_warnings=r['qualification_warnings']),
      'connection':dict(answer='Recorded communication losses remain in history after recovery; missing intervals are not reconstructed.',findings=[f for f in findings if f['issue_type']=='irrigation_telemetry'],observations=states),
      'evidence':dict(answer='Each finding links to observation hashes in the exported assessment. Hashes are not authenticated physical proof.',findings=findings,monitoring_policy=r['monitoring_policy'],observations_sha256=r['observations_sha256']),
      'flow':dict(answer='BLE valve status does not verify actual water flow. Separately supplied flow assertions are evaluated only under the recorded scope/timing policy; physical calibration and sampling are not verified.',flow_measurement_verified=False,flow_assertion_count=len(r['flow_observations'])),
      'consumption':dict(answer='Water consumption and water loss were not measured by this assessment. No litres are inferred from valve-open time.',measured_consumption_liters=None),
      'control':dict(answer='Physical actuation is unavailable. This read-only integration cannot start or stop watering.',actuator_control_enabled=False)}
    summary=' '.join(f"Observation {i+1}: reported valve {d['reported_valve_at_observation']}, watering {d['reported_active_watering']}, at {d['observed_at_utc']}; quality {d['quality']}, state at cutoff {d['current_valve_at_cutoff']}." for i,d in enumerate(states))
    for key in ('status','watering','observation'):result[key]['answer']+=' '+summary
    result['battery']['answer']+=' '+' '.join(f"Observation {i+1}: {d['reported_battery_percent'] if d['reported_battery_percent'] is not None else 'unavailable'}% at {d['observed_at_utc']}, quality {d['quality']}." for i,d in enumerate(states))
    result['duration']['answer']+=f" Configured limit: {r['monitoring_policy']['watering_limit_seconds']} seconds. "+' '.join(f['reason'] for f in result['duration']['findings'])
    result['warnings']['answer']+=f" {len(findings)} findings recorded."
    return {k:{**common,**v} for k,v in result.items()}


def intent(question):
    if not isinstance(question,str) or len(question)>500:raise TelemetryError('use a supported short irrigation question')
    text=question.lower().strip()
    if text in QUESTIONS:return text
    for key,value in QUESTIONS.items():
        if text==value.lower():return key
    if any(w in text for w in ('stop','start','close valve','open valve','schedule','firmware','reset')):return 'control'
    for words,key in [(('water loss','consum','litre','liter'),'consumption'),(('actually flowing','flow'),'flow'),
                      (('evidence','why','support'),'evidence'),(('battery',),'battery'),(('exceed','duration','long'),'duration'),
                      (('drop','disconnect','connection'),'connection'),(('warning','anomal'),'warnings'),
                      (('most recent','last valid','when'),'observation'),(('watering',),'watering'),(('state','status'),'status')]:
        if any(word in text for word in words):return key
    raise TelemetryError('unsupported question; use status, watering, observation, battery, duration, warnings, connection, evidence, flow, consumption or control')


def ask(view,question):return answers(view)[intent(question)]


# Shared handlers used by the standalone page and the optional hotel voice client.
# They return precomputed responses; no clocks, policy calculations or actuator path.
TOOLS_JS=r'''
function irrigationTools(data, openView) {
  const copy=value=>JSON.parse(JSON.stringify(value));
  const get=key=>copy(data[key]);
  return {
    get_irrigation_status:()=>get('status'),
    get_irrigation_findings:()=>get('warnings'),
    get_irrigation_observation:()=>get('observation'),
    explain_irrigation_finding:({finding_id}={})=>{
      const answer=get('evidence');
      if (finding_id) {
        answer.findings=answer.findings.filter(f=>f.finding_id===finding_id);
        if (!answer.findings.length) return {error:'Unknown finding; no evidence invented.'};
      }
      return answer;
    },
    open_irrigation_view:()=>{if(openView)openView();return {view:'gardena',static_report:true,actuator_control_enabled:false};},
    get_irrigation_flow:()=>get('flow'),
    get_irrigation_consumption:()=>get('consumption')
  };
}
'''


def section(view,voice_agent=None):
    import html
    data=answers(view)
    payload=json.dumps(data,sort_keys=True,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    options=''.join('<option value="'+k+'">'+html.escape(v)+'</option>' for k,v in QUESTIONS.items())
    content='<section id="questions"><h2>Ask the evidence</h2><p>Offline, deterministic answers from this exact assessment. No language model or microphone is needed.</p><label for="intent">Question</label> <select id="intent">'+options+'</select> <button id="ask" type="button">Show answer</button><p id="answer-summary" aria-live="polite"></p><details><summary>Structured answer and evidence</summary><pre id="answer"></pre></details>'
    if voice_agent:
        content+='<details><summary>Optional voice · network and microphone</summary><p>Explicit opt-in sends your speech and limited, alias-free status answers to ElevenLabs. No raw device identifiers or credentials are included. Agent responses are not independently verified; compare the evidence below. HTTPS or localhost may be required.</p><label><input id="voice-consent" type="checkbox"> I agree to the voice provider receiving speech and status summaries.</label> <button id="voice" type="button">Start voice</button><p id="voice-state" aria-live="polite">Not started</p></details>'
    content+='</section><script id="irrigation-answers" type="application/json">'+payload+'</script><script>'+TOOLS_JS+'''
const IA=JSON.parse(document.getElementById('irrigation-answers').textContent);
const IT=irrigationTools(IA,()=>document.getElementById('status').scrollIntoView());
const showAnswer=()=>{const answer=IA[document.getElementById('intent').value];document.getElementById('answer-summary').textContent=answer.answer;document.getElementById('answer').textContent=JSON.stringify(answer,null,2);};
document.getElementById('ask').onclick=showAnswer;showAnswer();
'''
    if voice_agent:
        # Agent ID is configuration, not a bearer credential; no value is inferred.
        content+='const agentId='+json.dumps(voice_agent).replace('<','\\u003c')+';'+r'''
let voiceCall=null;
document.getElementById('voice').onclick=async()=>{
 const status=document.getElementById('voice-state');
 if (voiceCall){await voiceCall.endSession();voiceCall=null;status.textContent='Ended';return;}
 if(!document.getElementById('voice-consent').checked){status.textContent='Explicit consent required; microphone not accessed.';return;}
 try {
   status.textContent='Connecting after opt-in';
   const mod=await import('https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.36.1/+esm');
   const clientTools={};for(const [key,fn] of Object.entries(IT))clientTools[key]=async args=>JSON.stringify(fn(args||{}));
   voiceCall=await mod.Conversation.startSession({agentId,connectionType:'webrtc',clientTools,
      onDisconnect:()=>{voiceCall=null;status.textContent='Disconnected';},
      onError:()=>{status.textContent='Voice unavailable; use offline questions.';}});
   status.textContent='Voice connected · static evidence, no control';
 }catch(error){status.textContent='Voice unavailable; use offline questions.';}
};
window.addEventListener('pagehide',()=>{if(voiceCall)voiceCall.endSession();});
'''
    return content+'</script>'
