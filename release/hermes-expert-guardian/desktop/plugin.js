import { host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const REASONS = {identical_failure:'Repeated failures', unsuccessful_approaches:'Several approaches failed', configuration_rewrite:'Repeated configuration changes', no_progress:'No progress detected', contradiction:'Action conflicts with evidence'}
const STATUS = {
  BLOCK_RETRIES:['Review the problem','You',0], AWAIT_EGRESS_APPROVAL:['Approve the summary','You',1],
  EXPERT_CONSULTATION:['Getting Expert advice','Expert',2], PROPOSED_FIX:['Review the proposed action','You',3],
  SINGLE_RETRY:['Ready for one corrective attempt','Hermes',3], AWAIT_ACTION_APPROVAL:['Corrective attempt awaiting result','Hermes / you',3],
  ESCALATE_TO_USER:['Needs your attention','You',3], REVIEWED:['Advice received — outcome not verified','Hermes / you',4],
  RESOLVED:['Resolved','Complete',5], AWAIT_SEND:['Approve the summary','You',1],
  REQUESTED:['Waiting for Hermes to prepare a summary','Hermes',0], PREPARING:['Preparing an anonymous summary','Hermes',0],
  SENDING:['Getting Expert advice','Expert',2], ADVICE_READY:['Advice ready','Hermes / you',3], FAILED:['Review failed','You',2], CANCELLED:['Review cancelled','You',0]
}
const STEPS = ['Review problem','Approve summary','Get advice','Take action','Verify result','Closed']
const box = {border:'1px solid #727b8880',borderRadius:8,padding:16,margin:'14px 0'}
const inputStyle = {display:'block',boxSizing:'border-box',width:'100%',padding:9,marginTop:5,border:'1px solid #727b88',borderRadius:5,background:'transparent',color:'inherit'}
const readable = key => key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase())
const status = item => item?.outcome_unresolved && item.state!=='RESOLVED' ? ['Outcome still unresolved','You',4] : item?.retry_ok && item.state!=='RESOLVED' ? ['Verify the result','You',4] : STATUS[item?.state] || ['Unknown status — reload before acting','You',0]
const heading = text => jsx('h3',{children:text})
const paragraph = text => jsx('p',{children:text})
const details = (title, children) => jsxs('details',{style:box,children:[jsx('summary',{children:title}),children]})
const fields = value => jsx('dl',{children:Object.entries(value || {}).map(([key,val])=>jsxs('div',{style:{margin:'10px 0'},children:[jsx('dt',{style:{fontWeight:600},children:readable(key)}),jsx('dd',{style:{margin:'4px 0',whiteSpace:'pre-wrap',overflowWrap:'anywhere'},children:Array.isArray(val) ? val.join('\n') || 'None reported' : typeof val==='object' ? JSON.stringify(val,null,2) : String(val)})]},key))})

function Settings({ctx}) {
  const activeSession = useValue(host.state.focusedStoredSessionId)
  const [session,setSession] = useState(activeSession || '')
  const [snapshot,setSnapshot] = useState(null)
  const [incident,setIncident] = useState('')
  const [review,setReview] = useState('')
  const [description,setDescription] = useState('')
  const [outcome,setOutcome] = useState('')
  const [tool,setTool] = useState('terminal')
  const [argumentsText,setArgumentsText] = useState('')
  const [verified,setVerified] = useState(false)
  const [verification,setVerification] = useState('')
  const [evidenceReviewed,setEvidenceReviewed] = useState(false)
  const [busy,setBusy] = useState(false)
  const [message,setMessage] = useState('')
  const [error,setError] = useState('')
  const [result,setResult] = useState(null)
  const currentSession = useRef(session.trim())
  currentSession.current = session.trim()
  const requestVersion = useRef(0)
  const mutationLock = useRef(false)
  const loaded = snapshot?.session===session.trim() ? snapshot : null
  const incidents = loaded?.incidents || []
  const reviews = loaded?.reviews || []
  const selected = incidents.find(i=>i.id===incident)
  const standalone = reviews.filter(r=>!r.incident)
  const related = reviews.filter(r=>r.incident===incident)
  const selectedReview = reviews.find(r=>r.id===review && !r.incident)
  const isLive = target => currentSession.current===target
  const clearForm = () => {setDescription('');setOutcome('');setTool('terminal');setArgumentsText('');setVerified(false);setVerification('');setEvidenceReviewed(false)}
  const chooseIncident = id => {setIncident(id);setReview('');clearForm();setMessage('');setError('')}
  const refresh = async (quiet=false) => {
    const target=session.trim(), version=++requestVersion.current
    if(!target){setError('Choose the chat containing your task first.');return}
    if(!quiet)setBusy(true)
    try {
      const data=await ctx.rest('/incident?session='+encodeURIComponent(target))
      if(!isLive(target) || version!==requestVersion.current)return
      const items=Array.isArray(data.incidents)?data.incidents:[]
      const advice=Array.isArray(data.reviews)?data.reviews:[]
      setSnapshot({...data,session:target,incidents:items,reviews:advice})
      if(!items.some(i=>i.id===incident)) {
        const open=items.filter(i=>i.state!=='RESOLVED')
        setIncident(open.length===1?open[0].id:items.length===1?items[0].id:'')
        clearForm()
      }
      if(!advice.some(r=>r.id===review)) {
        const pending=advice.filter(r=>r.state==='AWAIT_SEND' && !r.incident)
        setReview(pending.length===1?pending[0].id:'')
      }
      setError(Array.isArray(data.reviews)?'':'This backend does not expose advisory reviews. Restart Hermes to load the updated plugin backend.')
    } catch {
      if(isLive(target) && version===requestVersion.current){setSnapshot(null);setError('Could not load this chat. Check the session and connection, then reload.')}
    } finally {if(!quiet)setBusy(false)}
  }
  useEffect(()=>{setSnapshot(null);setIncident('');setReview('');clearForm();setMessage('');setError('');refresh()},[session])
  useEffect(()=>{
    const timer=setInterval(()=>{if(!busy && session.trim())refresh(true)},5000)
    return ()=>clearInterval(timer)
  },[session,busy,incident,review])
  const submit = (target,text) => {
    if(!host.composer.submit(target,text))setMessage('Waiting for Hermes. Open this chat and ask Hermes to continue the pending Guardian step.')
  }
  const act = async (action,extra={}) => {
    if(busy || mutationLock.current || !session.trim())return false
    mutationLock.current=true
    const target=session.trim(), identity=selected?.id
    ++requestVersion.current
    setBusy(true);setError('');setMessage('')
    try {
      const data=await ctx.rest('/action',{method:'POST',body:{session:target,incident:identity || '',action,...extra}})
      if(!isLive(target))return false
      setResult(data)
      if(action==='request_review') {
        setReview(data.review_id)
        submit(target,'Use guardian_review with review_id '+data.review_id+'. Prepare a focused diagnostic from our current task, then assess Expert advice against local evidence and continue under normal approvals.')
      }
      if(action==='send_review' && data.state==='ADVICE_READY')submit(target,'Retrieve guardian_review review_id '+extra.review_id+' and assess the advice against local evidence, then continue under normal approvals. Do not claim the incident resolved until the outcome is verified.')
      if(action==='authorize')submit(target,'Guardian incident '+identity+' has one exact corrective attempt authorized: '+JSON.stringify({tool:extra.tool,args:extra.args})+'. Success criteria: '+extra.criteria+'. Perform only this exact operation under native approval, then report the result. Do not claim resolution until user verification.')
      if(action==='reset'){setSnapshot(null);setIncident('');setReview('');clearForm()}
      else {setVerified(false);setEvidenceReviewed(false)}
      if(action!=='test')await refresh(true)
      setMessage(previous=>previous || (action==='resolve'?'Incident closed after your verification.':action==='test'?(data.passed?'Local safeguard checks passed. No cloud requests or real tools.':'Some safeguard checks failed. Open technical details.'):'Step saved. The current status and next action are shown below.'))
      return true
    } catch {
      if(isLive(target)){
        setError('This step could not be completed. Reload the current state before retrying. Check Expert settings, approval requirements and review limits. No success has been assumed.')
        setSnapshot(null)
      }
      return false
    } finally {mutationLock.current=false;setBusy(false)}
  }
  const button = (text,fn,disabled=false) => jsx('button',{type:'button',disabled:busy || disabled,onClick:fn,style:{padding:'9px 12px',margin:'5px 8px 5px 0',border:'1px solid #727b88',borderRadius:5,background:'transparent',color:'inherit'},children:text})
  const field = (label,value,change,multiline=false) => jsxs('label',{style:{display:'block',margin:'14px 0'},children:[label,jsx(multiline?'textarea':'input',{value,onChange:e=>change(e.target.value),rows:multiline?3:undefined,style:inputStyle})]})
  const check = (label,value,change) => jsxs('label',{style:{display:'block',margin:'14px 0'},children:[jsx('input',{type:'checkbox',checked:value,onChange:e=>change(e.target.checked)}),' '+label]})
  const continueChat = text => {setMessage('');submit(session.trim(),text)}
  const approval = (item,isIncident=false) => {
    const canApprove = item?.state===(isIncident?'AWAIT_EGRESS_APPROVAL':'AWAIT_SEND') && !!item.packet_hash && !!item.packet
    return jsxs('section',{style:box,children:[heading('Approve what Expert will receive'),paragraph('Read the exact summary below. Only this approved packet is sent. Expert routing is configured in Hermes auxiliary models → Expert.'),
      jsx('div',{'aria-label':isIncident?'Incident packet for approval':'Anonymous packet for approval',children:fields(item.packet)}),
      button('Approve summary and get advice',()=>act(isIncident?'send':'send_review',isIncident?{packet_hash:item.packet_hash}:{review_id:item.id,packet_hash:item.packet_hash}),!canApprove),
      button(isIncident?'Stop and keep incident open':'Cancel this review',()=>act(isIncident?'deny':'cancel_review',isIncident?{}:{review_id:item.id}))]})
  }
  const advice = item => item?.advice && jsxs('section',{style:box,children:[heading('Expert advice'),paragraph('Compare this recommendation with local evidence before acting.'),fields(item.advice)]})
  const reviewCard = item => item && jsxs('section',{style:box,children:[heading('Expert review · '+status(item)[0]),paragraph('Next actor: '+status(item)[1]+'.'+(item.round?' Round '+item.round+'.':'')),
    item.state==='AWAIT_SEND' && approval(item),advice(item),
    item.state==='ADVICE_READY' && button('Continue with Hermes',()=>continueChat('Retrieve guardian_review review_id '+item.id+'; compare the advice with evidence and continue under normal approvals. Verify the outcome with the user.')),
    item.state==='REQUESTED' && button('Ask Hermes to prepare summary',()=>continueChat('Use guardian_review with review_id '+item.id+' and prepare a focused diagnostic from the task.')),
    ['PREPARING','SENDING'].includes(item.state) && paragraph('Waiting for processing. This page refreshes automatically. If processing was interrupted, cancel this review before deliberately requesting another.'),
    item.state==='FAILED' && paragraph('The review could not complete. Check local summary / Expert settings. A new request still uses the session budget and cooldown.'),
    !['CANCELLED','ADVICE_READY'].includes(item.state) && button('Cancel this review',()=>act('cancel_review',{review_id:item.id})),
    details('Review technical details',fields(item))]},item.id)
  const currentStatus=status(selected)
  const canVerify=selected && selected.state!=='RESOLVED' && (selected.retry_ok || selected.state==='REVIEWED')
  return jsxs('main',{style:{padding:20,maxWidth:920,margin:'0 auto',lineHeight:1.5},children:[
    jsx('h2',{children:'Expert Guardian · Incidents'}),paragraph('Track the problem, review advice, take action and verify the outcome.'),
    jsxs('section',{style:box,children:[heading('Task chat'),paragraph(session?'Selected chat: '+session:'Open the chat containing your task, then use focused chat.'),
      button('Use focused chat',()=>setSession(activeSession || ''),!activeSession),button('Reload incidents and reviews',()=>refresh(),!session.trim()),
      details('Choose another chat',field('Durable session ID (from the chat URL)',session,value=>{setSession(value);clearForm()})),
      loaded && paragraph(loaded.mode==='enforce'?'Enforce mode: Guardian blocks repeated operations until an allowed next step.':'Monitor mode: incidents are recorded; Guardian does not block operations.')]}),
    error && jsx('p',{role:'alert',style:box,children:error}),message && jsx('p',{role:'status',style:box,children:message}),
    busy && paragraph('Loading or processing…'),
    loaded && jsxs('section',{style:box,children:[heading('Incidents in this chat'),
      !incidents.length && paragraph('No incidents recorded. You can still ask Expert for advice below.'),
      ...[...incidents].sort((a,b)=>(a.state==='RESOLVED')-(b.state==='RESOLVED') || (b.time || 0)-(a.time || 0)).map(i=>jsxs('article',{style:{padding:'10px 0',borderBottom:'1px solid #727b8840'},children:[
        jsx('strong',{children:REASONS[i.reason] || readable(i.reason || 'Incident')}),paragraph(status(i)[0]+' · Next: '+status(i)[1]+(i.time?' · '+new Date(i.time*1000).toLocaleString():'')),
        button(i.id===incident?'Viewing incident':'Open incident',()=>chooseIncident(i.id)),jsx('small',{children:'Reference '+i.id})]},i.id))]}),
    selected && jsxs('section',{'aria-label':'Incident journey',children:[
      heading(REASONS[selected.reason] || readable(selected.reason || 'Incident')),
      jsx('ol',{'aria-label':'Incident progress',style:{display:'flex',flexWrap:'wrap',gap:24,paddingLeft:24},children:STEPS.map((step,index)=>jsx('li',{'aria-current':index===currentStatus[2]?'step':undefined,style:{fontWeight:index===currentStatus[2]?700:400},children:step},step))}),
      jsxs('section',{style:box,children:[heading(currentStatus[0]),paragraph('Next actor: '+currentStatus[1]+'.'),paragraph('Observed '+(selected.attempts || 0)+' failed or repeated attempts. '+(selected.packet?.problem || 'Guardian detected a repeated pattern; the cause still needs review.'))]}),
      selected.state==='BLOCK_RETRIES' && jsxs('section',{style:box,children:[heading('1. Review the problem'),paragraph('Describe the problem and what a successful result looks like. Keep secrets and identifying details out of these fields.'),
        field('Problem to review',description,setDescription,true),field('What should success look like?',outcome,setOutcome,true),
        button('Prepare Expert review',()=>act('prepare',{description:description.trim(),outcome:outcome.trim()}),!description.trim() || !outcome.trim())]}),
      selected.state==='AWAIT_EGRESS_APPROVAL' && approval(selected,true),
      selected.state==='EXPERT_CONSULTATION' && paragraph('Expert is reviewing the approved summary. This page refreshes automatically.'),
      advice(selected),
      selected.state==='PROPOSED_FIX' && jsxs('section',{style:box,children:[heading('4. Review and approve one action'),paragraph('Expert advice grants no permission. Review the evidence, enter the exact action and define success. Hermes will also request its normal native approval.'),
        button('Ask Hermes to prepare the action',()=>continueChat('For Guardian incident '+selected.id+', compare Expert advice with local evidence and propose one exact corrective operation. Show the tool name, command or argument object, expected result and risks so I can review them in Guardian. Do not execute the operation before authorization.')),
        field('Tool name',tool,setTool),field(tool==='terminal'?'Command to run':'Tool arguments (JSON object)',argumentsText,setArgumentsText,true),
        field('Success criteria',outcome,setOutcome,true),check('I checked this action against the evidence.',evidenceReviewed,setEvidenceReviewed),
        button('Approve one corrective attempt',()=>{
          try {
            const args=tool.trim()==='terminal'?{command:argumentsText}:JSON.parse(argumentsText)
            if(!args || Array.isArray(args) || typeof args!=='object')throw Error('Invalid arguments')
            act('authorize',{tool:tool.trim(),args,criteria:outcome.trim(),evidence_reviewed:true})
          } catch {setError('Enter a valid JSON object for the selected tool arguments.')}
        },!evidenceReviewed || !tool.trim() || !argumentsText.trim() || !outcome.trim() || loaded.mode!=='enforce'),
        loaded.mode!=='enforce' && paragraph('Corrective authorization requires Enforce mode. Change mode deliberately in Agent settings before authorizing recovery.')]}),
      ['SINGLE_RETRY','AWAIT_ACTION_APPROVAL'].includes(selected.state) && paragraph('One exact attempt is authorized. Continue in the task chat and complete any native approval there. Guardian is waiting for the tool result; authorization alone does not mean it ran.'),
      selected.state==='REVIEWED' && paragraph('Advice released this incident’s previous block so Hermes can continue. The outcome remains unverified. Related reviews and their advice are below.'),
      selected.state==='REVIEWED' && button('Continue with Hermes',()=>continueChat('Retrieve guardian_review review_id '+selected.review_id+' for incident '+selected.id+'. Compare the advice with local evidence and continue under normal approvals. Report success checks; user verification is still required.')),
      (selected.outcome_unresolved || selected.state==='ESCALATE_TO_USER' && !selected.retry_ok) && jsxs('section',{style:box,children:[heading('Choose the next step'),paragraph(selected.outcome_unresolved?'The intended outcome has not been achieved. Keep this incident open and investigate the remaining problem. This does not grant another corrective attempt.':selected.retry_finished?'The corrective attempt did not succeed. This incident has no further corrective attempts available. Keep it open and investigate a different approach.':selected.expert_failure?'Expert review failed: '+readable(selected.expert_failure)+'. This incident remains open.':'Advice is inconclusive, more evidence is needed, or escalation was stopped. This incident remains open.'),
        paragraph('Ask Hermes to explain the evidence gaps and propose a different approach. This does not authorize another blocked operation or repeat consultation.'),
        button('Ask Hermes to investigate',()=>continueChat('Guardian incident '+selected.id+' remains unresolved. Explain the evidence gaps and propose a different approach under current permissions. Do not repeat blocked actions, reset history or claim resolution.'))]}),
      canVerify && jsxs('section',{style:box,children:[heading('5. Verify the result'),paragraph(selected.retry_ok?'The corrective tool reported success. Check the intended outcome before closing.':'Advice is available, but success has not been established. Check Hermes’s subsequent work before closing.'),
        paragraph('Success criteria: '+(selected.criteria || selected.packet?.intended_outcome || 'Record the checked outcome below.')),
        field('What did you check, and what was the result? (no secrets)',verification,setVerification,true),
        check('I verified the intended outcome was achieved.',verified,setVerified),
        button('Confirm resolved',()=>act('resolve',{verification:verification.trim()}),!verified || !verification.trim()),
        button('Still unresolved',()=>{setVerified(false);act('unresolved')})]}),
      selected.state==='RESOLVED' && jsxs('section',{style:box,children:[heading('Incident closed'),paragraph('You confirmed the outcome after checking the result.'),fields({problem:selected.packet?.problem || REASONS[selected.reason],success_criteria:selected.criteria || selected.packet?.intended_outcome || 'User verified outcome',verification:selected.verification || 'User verified corrective result'})]}),
      related.length>0 && jsxs('section',{children:[heading('Expert reviews for this incident'),...related.map(reviewCard)]}),
      details('Incident history and technical details',jsxs('div',{children:[jsx('ol',{children:[...(selected.transitions || []),...(selected.retry_finished?['Corrective attempt '+(selected.retry_ok?'reported success':'did not succeed')]:[]),...(selected.user_verified?['User verified outcome']:[])].map((event,index)=>jsx('li',{children:STATUS[event]?.[0] || readable(event)},index))}),fields(selected)]}))]}),
    loaded && details('Ask Expert · advice outside an incident',jsxs('div',{children:[paragraph('Use this for general task advice. These reviews do not close an incident.'),button('Request Expert advice',()=>act('request_review')),
      jsxs('label',{children:['Select a review',jsx('select',{style:inputStyle,value:review,onChange:e=>setReview(e.target.value),children:[jsx('option',{value:'',children:'Choose a review'}),...standalone.map(r=>jsx('option',{value:r.id,children:status(r)[0]+' · '+r.id},r.id))]})]}),
      reviewCard(selectedReview),!standalone.length && paragraph('No general advice requests in this chat.')]})),
    details('Advanced settings and maintenance',jsxs('div',{children:[paragraph('Expert provider/model, local summary model, conversation rounds and sending policy are configured in Hermes Agent settings and auxiliary models.'),
      button('Run local safeguard simulations (no cloud)',()=>act('test'),!session.trim()),
      button('Reset session and delete history',()=>{if(window.confirm('Delete this chat’s Guardian history and release its incident blocks? This is maintenance, not incident resolution.'))act('reset')},!session.trim()),
      result && details('Last action technical result',jsx('pre',{style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere'},children:JSON.stringify(result,null,2)}))]}))
  ]})
}
export default {
  id:'hermes-expert-guardian',name:'Expert Guardian',
  register(ctx) {ctx.registerSettingsPage?.({id:'guardian',title:'Expert Guardian',icon:'shield',render:()=>jsx(Settings,{ctx})})}
}
