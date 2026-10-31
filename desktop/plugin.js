import { host, useValue } from '@hermes/plugin-sdk'
import { useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function Settings({ ctx }) {
  const activeSession = useValue(host.state.focusedStoredSessionId)
  const [session, setSession] = useState(activeSession || '')
  const [incident, setIncident] = useState('')
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
    jsx('p',{children:'Agent settings below control monitoring and enforcement. Select the affected session ID. No terminal transcript is sent. Every cloud packet and corrective attempt needs your approval.'}),
    field('Durable session ID (from the chat URL)',session,setSession), field('Incident ID',incident,setIncident),
    button('Use focused session',()=>setSession(activeSession || '')),
    button('Run local safeguard simulations (no cloud)',()=>act('test')),
    button('Refresh incidents', async()=>{try{setResult(await ctx.rest('/incident?session='+encodeURIComponent(session)))}catch{host.notify({kind:'error',message:'Cannot load incidents'})}}),
    field('Public problem description (no secrets)',description,setDescription),field('Intended outcome / success criteria',outcome,setOutcome),
    button('Prepare diagnostic preview',()=>act('prepare',{description,outcome})),
    button('Approve sending preview to Codex',()=>{
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
