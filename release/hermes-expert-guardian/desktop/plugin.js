import { host, useValue } from '@hermes/plugin-sdk'
import { useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function Settings({ ctx }) {
  const activeSession = useValue(host.state.focusedStoredSessionId)
  const [session, setSession] = useState(activeSession || '')
  const [incident, setIncident] = useState('')
  const [review, setReview] = useState('')
  const [description, setDescription] = useState('')
  const [outcome, setOutcome] = useState('')
  const [operation, setOperation] = useState('{"tool":"terminal","args":{"command":""}}')
  const [result, setResult] = useState(null)
  const [reviewSnapshot, setReviewSnapshot] = useState(null)
  const [incidentSnapshot, setIncidentSnapshot] = useState(null)
  const [busy, setBusy] = useState(false)
  const selectedReview = reviewSnapshot?.session===session.trim()
    ? reviewSnapshot.reviews.find(r=>r.id===review.trim()) : null
  const canApprove = selectedReview?.state==='AWAIT_SEND' && !!selectedReview.packet_hash && !!selectedReview.packet
  const selectedIncident = incidentSnapshot?.session===session.trim()
    ? incidentSnapshot.incidents.find(i=>i.id===incident.trim()) : null
  const canApproveIncident = selectedIncident?.state==='AWAIT_EGRESS_APPROVAL' && !!selectedIncident.packet_hash && !!selectedIncident.packet
  const refresh = async () => {
    const target=session.trim()
    if(!target){host.notify({kind:'info',message:'Select the task’s durable session ID first.'});return}
    setBusy(true)
    try {
      const data=await ctx.rest('/incident?session='+encodeURIComponent(target))
      setResult(data)
      const reviews=Array.isArray(data.reviews)?data.reviews:[]
      const incidents=Array.isArray(data.incidents)?data.incidents:[]
      setReviewSnapshot({session:target,reviews})
      setIncidentSnapshot({session:target,incidents})
      if(!incidents.some(i=>i.id===incident.trim())) {
        const active=incidents.filter(i=>!['RESOLVED','REVIEWED'].includes(i.state))
        setIncident(active.length===1?active[0].id:incidents.length===1?incidents[0].id:'')
      }
      if(!reviews.some(r=>r.id===review.trim())) {
        const pending=reviews.filter(r=>r.state==='AWAIT_SEND')
        setReview(pending.length===1?pending[0].id:'')
      }
      if(!Array.isArray(data.reviews))host.notify({kind:'info',message:'This backend does not expose advisory reviews. Restart Hermes to load the updated plugin backend.'})
      else if(!reviews.length && !incidents.length)host.notify({kind:'info',message:'No incidents or reviews in this session. Use the session containing your task.'})
    }catch{setReviewSnapshot(null);setIncidentSnapshot(null);host.notify({kind:'error',message:'Cannot load reviews. Check the session ID and connection.'})}
    finally{setBusy(false)}
  }
  const field = (label, value, change) => jsxs('label', { style:{display:'block',margin:'12px 0'}, children:[label, jsx('input', {value, onChange:e=>change(e.target.value), style:{display:'block',width:'100%',padding:'8px',marginTop:'4px',border:'1px solid #68707c',borderRadius:'4px',background:'transparent',color:'inherit'}})] })
  const act = async (action, extra={}) => {
    setBusy(true)
    try {
      setResult(await ctx.rest('/action', {method:'POST', body:{session:session.trim(), incident:incident.trim(), action, ...extra}}))
      if(action==='cancel_review' || action==='reset')setReviewSnapshot(null)
      if(action==='reset')setIncidentSnapshot(null)
      else if(['prepare','send','deny','authorize','resolve'].includes(action))await refresh()
    }
    catch { host.notify({kind:'error',message:'Guardian action refused; check incident state and privacy constraints.'}) }
    finally { setBusy(false) }
  }
  const button = (text, fn) => jsx('button', {type:'button',disabled:busy,onClick:fn,style:{margin:'8px',padding:'8px',border:'1px solid'},children:text})
  return jsxs('div', {style:{padding:'20px',maxWidth:'850px'},children:[
    jsx('h2',{children:'Expert Guardian'}),
    jsx('p',{children:'Conversation settings are in this plugin’s Agent settings: expert_conversations enables follow-ups; conversation_max_rounds limits total Expert replies (1–6); conversation_approve_each_round requires approval of every follow-up. Every round is locally anonymised and validated; privacy checks cannot be disabled. Leave per-round approval on for sensitive tasks.'}),
    jsx('p',{children:'Request advice for the selected session. Hermes prepares a diagnostic, the configured local model anonymises it, and Expert receives only the validated summary. Sending follows your preview/automatic policy. Hermes continues using its normal approvals.'}),
    field('Durable session ID (from the chat URL)',session,setSession), field('Incident ID',incident,setIncident),
    button('Use focused session',()=>setSession(activeSession || '')),
    button('Request Expert review and continue',async()=>{
      const target=session
      setBusy(true)
      try {
        const request=await ctx.rest('/action',{method:'POST',body:{session:target,action:'request_review'}})
        setReview(request.review_id);setResult(request)
        const sent=host.composer.submit(target,'Use guardian_review with review_id '+request.review_id+'. Prepare a focused diagnostic from our current task: problem, intended outcome, evidence, failed approaches and question. After Expert advice is available, assess it against local evidence and continue the task using normal approvals.')
        if(!sent)host.notify({kind:'info',message:'Review queued. Open this session and ask Hermes to continue the pending Guardian review.'})
      }catch{host.notify({kind:'error',message:'Review request refused; check settings and session budget.'})}
      finally{setBusy(false)}
    }),
    field('Review ID (from request or review history)',review,setReview),
    button('Load / refresh reviews for this session',refresh),
    reviewSnapshot?.session===session.trim() && jsxs('label',{style:{display:'block',margin:'12px 0'},children:[
      'Select a review',jsx('select',{value:review.trim(),onChange:e=>setReview(e.target.value),style:{display:'block',width:'100%',padding:'8px'},children:[
        jsx('option',{value:'',children:'Choose a review'}),
        ...reviewSnapshot.reviews.map(r=>jsx('option',{value:r.id,children:r.id+' — '+r.state+(r.round?' — round '+r.round:'')},r.id))
      ]})
    ]}),
    jsx('p',{children:selectedReview
      ? 'Selected review: '+selectedReview.id+' — '+selectedReview.state+'. Inspect the anonymous packet below before approving.'
      : 'Load reviews for the task’s session, then select a review. Pending reviews are separate from legacy incidents.'}),
    selectedReview?.packet && jsx('pre',{'aria-label':'Anonymous packet for approval',style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere',padding:'12px',border:'1px solid'},children:JSON.stringify(selectedReview.packet,null,2)}),
    jsx('button',{type:'button',disabled:busy || !canApprove,style:{margin:'8px',padding:'8px',border:'1px solid'},children:'Approve reviewed summary and continue',onClick:async()=>{
      if(!canApprove)return
      const item=selectedReview
      const target=session.trim()
      setBusy(true)
      try{
        const advice=await ctx.rest('/action',{method:'POST',body:{session:target,action:'send_review',review_id:item.id,packet_hash:item.packet_hash}})
        setReviewSnapshot(null)
        setResult(advice)
        if(advice.state==='ADVICE_READY' && !host.composer.submit(target,'Retrieve guardian_review review_id '+item.id+' and assess the advice against local evidence, then continue our task using normal approvals.'))host.notify({kind:'info',message:'Advice ready. Open this session and ask Hermes to retrieve the pending review.'})
      }catch{setReviewSnapshot(null);host.notify({kind:'error',message:'Approval refused. Reload reviews and inspect the current packet; it may have changed or already been sent.'})}
      finally{setBusy(false)}
    }}),
    button('Cancel selected review',()=>act('cancel_review',{review_id:review})),
    button('Run local safeguard simulations (no cloud)',()=>act('test')),
    button('Refresh incidents',refresh),
    incidentSnapshot?.session===session.trim() && jsxs('label',{style:{display:'block',margin:'12px 0'},children:[
      'Select an incident',jsx('select',{value:incident.trim(),onChange:e=>setIncident(e.target.value),style:{display:'block',width:'100%',padding:'8px'},children:[
        jsx('option',{value:'',children:'Choose an incident'}),
        ...incidentSnapshot.incidents.map(i=>jsx('option',{value:i.id,children:i.id+' — '+i.reason+' — '+i.state},i.id))
      ]})
    ]}),
    jsx('p',{children:selectedIncident
      ? 'Selected incident: '+selectedIncident.id+' — '+selectedIncident.reason+' — '+selectedIncident.state
      : 'Refresh incidents for this session, then choose an incident from the list.'}),
    selectedIncident?.packet && jsx('pre',{'aria-label':'Incident packet for approval',style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere',padding:'12px',border:'1px solid'},children:JSON.stringify(selectedIncident.packet,null,2)}),
    field('Public problem description (no secrets)',description,setDescription),field('Intended outcome / success criteria',outcome,setOutcome),
    button('Prepare diagnostic preview',()=>act('prepare',{description,outcome})),
    jsx('p',{children:'Choose your preferred provider and model in Hermes → Model → Auxiliary models → Expert. Hermes manages authentication and routing. Review that destination before approving a packet.'}),
    jsx('button',{type:'button',disabled:busy || !canApproveIncident,style:{margin:'8px',padding:'8px',border:'1px solid'},children:'Approve sending preview to Expert',onClick:()=>{
      if(canApproveIncident)act('send',{packet_hash:selectedIncident.packet_hash})
    }}),
    button('Deny escalation / stop',()=>act('deny')),
    field('Exact corrective operation JSON',operation,setOperation),
    button('I reviewed evidence; authorize one attempt',()=>{
      try {const op=JSON.parse(operation);act('authorize',{...op,criteria:outcome,evidence_reviewed:true})}
      catch {host.notify({kind:'error',message:'Invalid operation JSON'})}
    }),
    button('I verified success criteria; resolve',()=>act('resolve')),
    button('Reset session and delete history',()=>{if(window.confirm('Release blocks and delete this session’s incident history?'))act('reset')}),
    jsx('pre',{style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere'},children:JSON.stringify(result,null,2)})
  ]})
}
export default {
  id:'hermes-expert-guardian',name:'Expert Guardian',
  register(ctx) { ctx.registerSettingsPage?.({id:'guardian',title:'Expert Guardian',icon:'shield',render:()=>jsx(Settings,{ctx})}) }
}
