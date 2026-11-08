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
  const [busy, setBusy] = useState(false)
  const field = (label, value, change) => jsxs('label', { style:{display:'block',margin:'12px 0'}, children:[label, jsx('input', {value, onChange:e=>change(e.target.value), style:{display:'block',width:'100%',padding:'8px',marginTop:'4px',border:'1px solid #68707c',borderRadius:'4px',background:'transparent',color:'inherit'}})] })
  const act = async (action, extra={}) => {
    setBusy(true)
    try { setResult(await ctx.rest('/action', {method:'POST', body:{session, incident, action, ...extra}})) }
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
    button('Approve reviewed summary and continue',async()=>{
      const item=result?.reviews?.find(r=>r.id===review)
      if(!item?.packet_hash || item.state!=='AWAIT_SEND'){host.notify({kind:'info',message:'Refresh incidents and review the exact anonymous packet before approving.'});return}
      const target=session
      setBusy(true)
      try{
        const advice=await ctx.rest('/action',{method:'POST',body:{session:target,action:'send_review',review_id:review,packet_hash:item.packet_hash}})
        setResult(advice)
        if(advice.state==='ADVICE_READY' && !host.composer.submit(target,'Retrieve guardian_review review_id '+review+' and assess the advice against local evidence, then continue our task using normal approvals.'))host.notify({kind:'info',message:'Advice ready. Open this session and ask Hermes to retrieve the pending review.'})
      }catch{host.notify({kind:'error',message:'Review sending refused.'})}
      finally{setBusy(false)}
    }),
    button('Cancel selected review',()=>act('cancel_review',{review_id:review})),
    button('Run local safeguard simulations (no cloud)',()=>act('test')),
    button('Refresh incidents', async()=>{try{setResult(await ctx.rest('/incident?session='+encodeURIComponent(session)))}catch{host.notify({kind:'error',message:'Cannot load incidents'})}}),
    field('Public problem description (no secrets)',description,setDescription),field('Intended outcome / success criteria',outcome,setOutcome),
    button('Prepare diagnostic preview',()=>act('prepare',{description,outcome})),
    jsx('p',{children:'Choose your preferred provider and model in Hermes → Model → Auxiliary models → Expert. Hermes manages authentication and routing. Review that destination before approving a packet.'}),
    button('Approve sending preview to Expert',()=>{
      const item=result?.incidents?.find(i=>i.id===incident)
      if(!item?.packet_hash || item.state!=='AWAIT_EGRESS_APPROVAL') {host.notify({kind:'info',message:'Refresh incidents and review the exact packet before approving.'});return}
      act('send',{packet_hash:item.packet_hash})
    }),
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
