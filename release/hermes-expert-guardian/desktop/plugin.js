import { host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const REASONS = {identical_failure:'Repeated failures', unsuccessful_approaches:'Several approaches failed', configuration_rewrite:'Repeated configuration changes', no_progress:'No progress detected', contradiction:'Action conflicts with evidence'}
const STATUS = {
  BLOCK_RETRIES:['Review the problem','You',0], AWAIT_EGRESS_APPROVAL:['Approve the summary','You',1],
  EXPERT_CONSULTATION:['Getting Expert advice','Expert',2], PROPOSED_FIX:['Review the proposed action','You',3],
  SINGLE_RETRY:['Ready for one corrective attempt','Hermes',3], AWAIT_ACTION_APPROVAL:['Corrective attempt awaiting result','Hermes / you',3],
  ESCALATE_TO_USER:['Needs your attention','You',3], REVIEWED:['Advice received — outcome not verified','Hermes / you',4],
  DISMISSED:['Closed without review','Complete',5], RESOLVED:['Resolved','Complete',5], AWAIT_SEND:['Approve the summary','You',1],
  REQUESTED:['Waiting for Hermes to prepare a summary','Hermes',0], PREPARING:['Preparing an anonymous summary','Hermes',0],
  SENDING:['Getting Expert advice','Expert',2], ADVICE_READY:['Advice ready','Hermes / you',3], FAILED:['Review failed','You',2], CANCELLED:['Review cancelled','You',0]
}
const DRAFT_STATUS = {PENDING:'Local draft pending',QUEUED:'Waiting for the local model',GENERATING:'Your local model is drafting the incident',READY:'Drafted by your local model',UNAVAILABLE:'Local model is not configured',FAILED:'Local drafting could not complete'}
const TRIGGERS = {identical_failure:'The same operation returned the same failure repeatedly.',unsuccessful_approaches:'Several different approaches failed within this task.',configuration_rewrite:'Repeated file or configuration changes did not establish progress.',no_progress:'Repeated observations returned unchanged results.',contradiction:'A proposed file change conflicts with recent local evidence.'}
const incidentTitle = item => {const text=item.problem_statement || REASONS[item.reason] || 'Incident';return text.length>120?text.slice(0,117)+'…':text}
const CLOSED = new Set(['RESOLVED','DISMISSED'])
const STEPS = ['Review problem','Approve summary','Get advice','Take action','Verify result','Closed']
const box = {border:'1px solid #727b8880',borderRadius:8,padding:16,margin:'14px 0'}
const inputStyle = {display:'block',boxSizing:'border-box',width:'100%',padding:9,marginTop:5,border:'1px solid #727b88',borderRadius:5,background:'transparent',color:'inherit'}
const readable = key => key.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase())
const status = item => item?.outcome_unresolved && !CLOSED.has(item.state) ? ['Outcome still unresolved','You',4] : item?.retry_ok && !CLOSED.has(item.state) ? ['Verify the result','You',4] : STATUS[item?.state] || ['Unknown status — reload before acting','You',0]
const chatName = row => [row?.title,row?.preview].find(value=>typeof value==='string' && value.trim() && ![row?.id,row?._lineage_root_id,row?.resolved_id].includes(value.trim()))?.trim() || 'Untitled chat'
const dated = value => value ? new Date(value*1000).toLocaleString() : 'Date unavailable'
const heading = text => jsx('h3',{children:text})
const paragraph = text => jsx('p',{children:text})
const details = (title, children) => jsxs('details',{style:box,children:[jsx('summary',{children:title}),children]})
const fields = value => jsx('dl',{children:Object.entries(value || {}).map(([key,val])=>jsxs('div',{style:{margin:'10px 0'},children:[jsx('dt',{style:{fontWeight:600},children:readable(key)}),jsx('dd',{style:{margin:'4px 0',whiteSpace:'pre-wrap',overflowWrap:'anywhere'},children:Array.isArray(val) ? val.join('\n') || 'None reported' : typeof val==='object' ? JSON.stringify(val,null,2) : String(val)})]},key))})

function Settings({ctx}) {
  const activeSession = useValue(host.state.focusedStoredSessionId)
  const profile = useValue(host.state.profile)
  const focusedProfile = useValue(host.state.focusedSessionProfile)
  const focusedChat = !focusedProfile || focusedProfile===profile ? activeSession : null
  const [session,setSession] = useState(focusedChat || '')
  const [chatSnapshot,setChatSnapshot] = useState(null)
  const [chatError,setChatError] = useState('')
  const [chatSearch,setChatSearch] = useState('')
  const [expandedChats,setExpandedChats] = useState(focusedChat ? [focusedChat] : [])
  const pendingIncident = useRef(null)
  const currentIncident = useRef('')
  const viewport = useValue(host.state.viewport)
  const chatVersion = useRef(0)
  const currentProfile = useRef(profile)
  currentProfile.current=profile
  const chats = chatSnapshot?.profile===profile ? chatSnapshot.chats : []
  const chatRow = chats.find(row=>row.id===session || row._lineage_root_id===session || row.resolved_id===session)
  const optionName = row => {
    const name=chatName(row), peers=chats.filter(other=>chatName(other)===name)
    return peers.length>1 ? name+' · '+dated(row.started_at)+' · Chat '+(peers.indexOf(row)+1) : name
  }
  const selectedChatName = chatRow ? optionName(chatRow) : session===focusedChat ? 'Current chat' : 'Chat unavailable'
  const loadChats = async () => {
    const target=profile, version=++chatVersion.current
    try {
      const [data,index]=await Promise.all([host.request('session.list',{profile:target,limit:1000}),ctx.rest('/incidents')])
      if(target!==currentProfile.current || version!==chatVersion.current)return
      if(!Array.isArray(data?.sessions))throw Error('Invalid chat list')
      if(!Array.isArray(index?.sessions))throw Error('Invalid incident list')
      setChatSnapshot({profile:target,chats:data.sessions.filter(row=>typeof row.id==='string' && row.id),index:index.sessions})
      setChatError('')
    } catch {
      if(target===currentProfile.current && version===chatVersion.current){setChatSnapshot(null);setChatError('Chat names could not be loaded. Open the task chat and use focused chat, or reload the chat list.')}
    }
  }
  const [snapshot,setSnapshot] = useState(null)
  const [incident,setIncident] = useState('')
  currentIncident.current=incident
  const [review,setReview] = useState('')
  const [dismissOpen,setDismissOpen] = useState(false)
  const [dismissReason,setDismissReason] = useState('Not relevant for review')
  const draftForm = useRef({key:'',problemDirty:false,outcomeDirty:false})
  const draftRequested = useRef(new Set())
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
  const loaded = snapshot?.session===session.trim() && snapshot?.profile===profile ? snapshot : null
  const incidents = loaded?.incidents || []
  const reviews = loaded?.reviews || []
  const selected = incidents.find(i=>i.id===incident)
  const standalone = reviews.filter(r=>!r.incident)
  const related = reviews.filter(r=>r.incident===incident)
  const selectedReview = reviews.find(r=>r.id===review && !r.incident)
  const isLive = target => currentSession.current===target && currentProfile.current===profile
  const clearForm = () => {draftForm.current={key:'',problemDirty:false,outcomeDirty:false};setDismissOpen(false);setDismissReason('Not relevant for review');setDescription('');setOutcome('');setTool('terminal');setArgumentsText('');setVerified(false);setVerification('');setEvidenceReviewed(false)}
  const chooseIncident = (id,target=session) => {
    pendingIncident.current={session:target,id}
    currentIncident.current=id
    setSession(target);setIncident(id);setSnapshot(null);setReview('');clearForm();setMessage('');setError('')
    if(target===session)refresh()
  }
  const chatKeys = row => [row.id,row._lineage_root_id,row.resolved_id].filter(Boolean)
  const toggleChat = row => setExpandedChats(previous=>chatKeys(row).some(key=>previous.includes(key))?previous.filter(key=>!chatKeys(row).includes(key)):[...previous,row.id])
  const treeKey = (event,row,child=false) => {
    const nodes=[...event.currentTarget.closest('[role=tree]').querySelectorAll('button[role=treeitem]')]
    const at=nodes.indexOf(event.currentTarget)
    if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
      event.preventDefault();nodes[event.key==='Home'?0:event.key==='End'?nodes.length-1:Math.max(0,Math.min(nodes.length-1,at+(event.key==='ArrowDown'?1:-1)))]?.focus()
    } else if(event.key==='ArrowRight' && !child && !chatKeys(row).some(key=>expandedChats.includes(key))){event.preventDefault();toggleChat(row)}
    else if(event.key==='ArrowLeft'){
      event.preventDefault()
      if(child)nodes.find(node=>node.value===row.id)?.focus()
      else if(chatKeys(row).some(key=>expandedChats.includes(key)))toggleChat(row)
    }
  }
  const refresh = async (quiet=false) => {
    const target=session.trim(), version=++requestVersion.current
    if(!target){setError('Choose the chat containing your task first.');return}
    if(!quiet)setBusy(true)
    try {
      const data=await ctx.rest('/incident?session='+encodeURIComponent(target))
      if(!isLive(target) || version!==requestVersion.current)return
      const items=Array.isArray(data.incidents)?data.incidents:[]
      const advice=Array.isArray(data.reviews)?data.reviews:[]
      setSnapshot({...data,session:target,profile,incidents:items,reviews:advice})
      if(!items.some(i=>i.id===currentIncident.current)) {setIncident('');clearForm()}
      if(!advice.some(r=>r.id===review)) {
        const pending=advice.filter(r=>r.state==='AWAIT_SEND' && !r.incident)
        setReview(pending.length===1?pending[0].id:'')
      }
      setError(Array.isArray(data.reviews)?'':'This backend does not expose advisory reviews. Restart Hermes to load the updated plugin backend.')
    } catch {
      if(isLive(target) && version===requestVersion.current){setSnapshot(null);setError('Could not load this incident. Refresh the tree and select it again.')}
    } finally {if(!quiet)setBusy(false)}
  }
  useEffect(()=>{setChatSnapshot(null);setExpandedChats(focusedChat?[focusedChat]:[]);setSession(focusedChat || '');loadChats()},[profile])
  useEffect(()=>{loadChats()},[activeSession])
  useEffect(()=>{setSnapshot(null);if(pendingIncident.current?.session!==session)setIncident('');pendingIncident.current=null;setReview('');clearForm();setMessage('');setError('');refresh()},[session,profile])
  useEffect(()=>{
    const timer=setInterval(()=>{if(!busy){if(session.trim())refresh(true);loadChats()}},5000)
    return ()=>clearInterval(timer)
  },[session,busy,incident,review,profile])
  useEffect(()=>{
    if(!selected)return
    const key=profile+'|'+session+'|'+incident
    if(draftForm.current.key!==key)draftForm.current={key,problemDirty:false,outcomeDirty:false}
    if(!draftForm.current.problemDirty)setDescription(selected.packet?.problem || selected.problem_statement || '')
    if(!draftForm.current.outcomeDirty)setOutcome(selected.criteria || selected.packet?.intended_outcome || selected.expected_outcome || '')
    if(!selected.draft_status && !CLOSED.has(selected.state) && !draftRequested.current.has(key)){
      draftRequested.current.add(key)
      const target=session
      ctx.rest('/action',{method:'POST',body:{session:target,incident,action:'draft_incident'}})
        .then(()=>{if(isLive(target))refresh(true)})
        .catch(()=>{if(isLive(target))setError('The local draft could not start. Reload the incident and try Generate local draft.')})
    }
  },[profile,session,incident,selected?.id,selected?.problem_statement,selected?.expected_outcome,selected?.draft_status,selected?.packet_hash])
  const submit = async (target,text,route) => {
    if(route){
      try {await ctx.rest('/action',{method:'POST',body:{session:target,action:'handoff',...route}})}
      catch {if(isLive(target))setError('The selected step has changed. Reload and select it again before continuing.');return}
    }
    if(!isLive(target))return
    if(!host.composer.submit(target,text))setMessage('Waiting for Hermes. Open “'+selectedChatName+'” and ask Hermes to continue the pending Guardian step.')
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
        await submit(target,'Prepare the selected Guardian review for this chat, then assess Expert advice against local evidence and continue under normal approvals. Use the internal Guardian context to identify the selected review.',{intent:'prepare_review',review_id:data.review_id})
      }
      if(action==='send_review' && data.state==='ADVICE_READY')await submit(target,'Continue the selected Expert review for this chat. Assess its advice against local evidence and continue under normal approvals. Verify the outcome before claiming resolution.',{intent:'continue_review',review_id:extra.review_id})
      if(action==='authorize')await submit(target,'The selected Guardian incident has one corrective attempt authorized: '+JSON.stringify({tool:extra.tool,args:extra.args})+'. Success criteria: '+extra.criteria+'. Perform only this exact operation under native approval, then report the result. Do not claim resolution until user verification.',{intent:'execute_action',incident:identity})
      if(action==='reset'){setSnapshot(null);setIncident('');setReview('');clearForm()}
      else {setVerified(false);setEvidenceReviewed(false);setDismissOpen(false)}
      if(action!=='test')await Promise.all([refresh(true),loadChats()])
      setMessage(previous=>previous || (action==='draft_incident'?'Local drafting requested. This does not send anything to Expert.':action==='dismiss'?'Incident closed without review. Closing it did not authorize or verify a correction.':action==='resolve'?'Incident closed after your verification.':action==='test'?(data.passed?'Local safeguard checks passed. No cloud requests or real tools.':'Some safeguard checks failed. Open safeguard check results.'):'Step saved. The current status and next action are shown below.'))
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
  const continueChat = (text,route) => {setMessage('');return submit(session.trim(),text,route)}
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
    item.state==='ADVICE_READY' && button('Continue with Hermes',()=>continueChat('Continue the selected Expert review. Compare its advice with evidence and continue under normal approvals. Verify the outcome with me.',{intent:'continue_review',review_id:item.id})),
    item.state==='REQUESTED' && button('Ask Hermes to prepare summary',()=>continueChat('Prepare a focused diagnostic for the selected Guardian review from this task.',{intent:'prepare_review',review_id:item.id})),
    ['PREPARING','SENDING'].includes(item.state) && paragraph('Waiting for processing. This page refreshes automatically. If processing was interrupted, cancel this review before deliberately requesting another.'),
    item.state==='FAILED' && paragraph('The review could not complete. Check local summary / Expert settings. A new request still uses the session budget and cooldown.'),
    !['CANCELLED','ADVICE_READY'].includes(item.state) && button('Cancel this review',()=>act('cancel_review',{review_id:item.id})),
    details('Review summary',fields({status:status(item)[0],requested:dated(item.time),round:item.round || 1}))]},item.id)
  const currentStatus=status(selected)
  const canVerify=selected && !CLOSED.has(selected.state) && (selected.retry_ok || selected.state==='REVIEWED')
  const treeRows=chats.length?chats:(focusedChat?[{id:focusedChat,title:'Current chat'}]:[])
  const treeIndex=chatSnapshot?.profile===profile?chatSnapshot.index || []:[]
  const incidentRows = row => {
    const cached=treeIndex.filter(entry=>chatKeys(row).includes(entry.session))
    if(loaded && chatKeys(row).includes(session) && !cached.some(entry=>entry.session===session))cached.push({session,incidents})
    const items=cached.flatMap(entry=>(entry.session===session && loaded?incidents:entry.incidents).map(item=>({...item,owner:entry.session})))
    return [...items].sort((a,b)=>Number(CLOSED.has(a.state))-Number(CLOSED.has(b.state)) || (b.time || 0)-(a.time || 0))
  }
  const openChats=treeRows.filter(row=>incidentRows(row).some(item=>!CLOSED.has(item.state)))
  const visibleChats=openChats.filter(row=>row.id===session || optionName(row).toLowerCase().includes(chatSearch.toLowerCase()))
  return jsxs('main',{style:{padding:20,maxWidth:1440,margin:'0 auto',lineHeight:1.5},children:[
    jsx('h2',{children:'Expert Guardian'}),paragraph('Choose a chat and incident on the left. Follow the steps on the right.'),
    jsxs('div',{'aria-label':'Incident workspace',style:{display:'grid',gridTemplateColumns:viewport?.narrow?'minmax(0, 1fr)':'minmax(260px, 32%) minmax(0, 1fr)',gap:24,alignItems:'start'},children:[
      jsxs('aside',{'aria-label':'Chats and incidents',style:{...box,margin:0,position:viewport?.narrow?'static':'sticky',top:12,maxHeight:viewport?.narrow?360:'75vh',overflowY:'auto',minWidth:0},children:[
        heading('Chats and incidents'),field('Find a chat by name',chatSearch,setChatSearch),
        button('Refresh tree',loadChats),button('Use focused chat',()=>{if(focusedChat){setExpandedChats(previous=>previous.includes(focusedChat)?previous:[...previous,focusedChat]);chooseIncident('',focusedChat);loadChats()}},!focusedChat || !openChats.some(row=>chatKeys(row).includes(focusedChat))),
        chatError && jsx('p',{role:'alert',children:chatError}),
        !openChats.length && paragraph(chatSnapshot?'No chats with open incidents.':chatError?'Refresh the tree to load open incidents.':'Loading chats with open incidents…'),
        openChats.length>0 && !visibleChats.length && paragraph('No matching chats with open incidents.'),
        jsx('ul',{role:'tree','aria-label':'Chat incident tree',style:{listStyle:'none',padding:0,margin:0},children:visibleChats.map(row=>{
          const items=incidentRows(row), expanded=chatKeys(row).some(key=>expandedChats.includes(key))
          return jsxs('li',{role:'none',style:{margin:'8px 0'},children:[
            jsx('button',{type:'button',role:'treeitem',value:row.id,'aria-expanded':expanded,'aria-label':optionName(row),onClick:()=>toggleChat(row),onKeyDown:event=>treeKey(event,row),style:{...inputStyle,textAlign:'left',fontWeight:600,overflowWrap:'anywhere',cursor:'pointer',margin:0},children:(expanded?'▾ ':'▸ ')+optionName(row)+' ('+items.length+')'}),
            expanded && jsx('ul',{role:'group',style:{listStyle:'none',padding:'4px 0 4px 16px'},children:items.length?items.map((item,index)=>jsx('li',{role:'none',children:jsxs('button',{type:'button',role:'treeitem',value:item.id,'aria-selected':session===item.owner && incident===item.id,'aria-label':incidentTitle(item)+' · '+dated(item.time)+' · Incident '+(index+1),onClick:()=>chooseIncident(item.id,item.owner),onKeyDown:event=>treeKey(event,row,true),style:{...inputStyle,textAlign:'left',cursor:'pointer',margin:'6px 0',borderWidth:session===item.owner && incident===item.id?2:1,fontWeight:session===item.owner && incident===item.id?600:400},children:[jsx('span',{style:{display:'block'},children:incidentTitle(item)}),jsx('small',{style:{display:'block'},children:(session===item.owner && incident===item.id?'Selected · ':'')+status(item)[0]}),jsx('small',{style:{display:'block'},children:dated(item.time)})]})},item.owner+':'+item.id)):jsx('li',{children:paragraph(chatSnapshot?'No incidents recorded.':'Loading incidents…')})})
          ]},row.id)
        })})
      ]}),
      jsxs('section',{'aria-label':'Selected incident',style:{minWidth:0},children:[
        error && jsx('p',{role:'alert',style:box,children:error}),message && jsx('p',{role:'status',style:box,children:message}),
        busy && paragraph('Loading or processing…'),
        !selected && jsxs('section',{style:box,children:[heading('Select an incident'),paragraph('Expand a chat on the left, then choose an incident to see its details and next step. No action is taken when you select an incident.')]}),
    selected && jsxs('section',{'aria-label':'Incident journey',children:[
      paragraph('Chat: '+selectedChatName),heading(REASONS[selected.reason] || 'Incident'),paragraph('Detected: '+dated(selected.time)),
      button('Reload incident',()=>refresh()),
      !CLOSED.has(selected.state) && button('Close without review',()=>setDismissOpen(true),!!selected.consumed && !selected.retry_finished),
      !CLOSED.has(selected.state) && selected.consumed && !selected.retry_finished && paragraph('Wait for the corrective attempt to finish before closing this incident.'),
      dismissOpen && !CLOSED.has(selected.state) && jsxs('section',{style:box,children:[heading('Close this incident without review?'),
        paragraph('This closes the incident and releases its Guardian retry block. It does not mark the problem as fixed or authorize any action. Normal Hermes approvals still apply.'),
        paragraph('Linked reviews will stop. A request already sent to Expert cannot be retracted. New repeated failures can create a new incident.'),
        field('Reason for closing (no secrets)',dismissReason,setDismissReason),
        button('Close incident',()=>act('dismiss',{reason:dismissReason.trim(),confirmed:true}),!dismissReason.trim()),button('Keep incident open',()=>setDismissOpen(false))]}),
      jsx('ol',{'aria-label':'Incident progress',style:{display:'grid',gridTemplateColumns:'repeat(3, minmax(0, 1fr))',gap:8,padding:0,listStyle:'none'},children:STEPS.map((step,index)=>jsx('li',{'aria-current':index===currentStatus[2]?'step':undefined,style:{fontWeight:index===currentStatus[2]?700:400,padding:8,border:'1px solid currentColor',borderRadius:5},children:(index+1)+'. '+step},step))}),
      jsxs('section',{style:box,children:[heading('Step '+(currentStatus[2]+1)+' of '+STEPS.length+' · '+currentStatus[0]),paragraph('Who acts next: '+currentStatus[1]+'.'),paragraph('Why this incident was generated: '+(selected.trigger_explanation || TRIGGERS[selected.reason] || 'Guardian detected repeated operations requiring attention.')),paragraph('Observed '+(selected.attempts || 0)+' failed or repeated attempts.')]}),
      selected.state!=='BLOCK_RETRIES' && !CLOSED.has(selected.state) && jsxs('section',{style:box,children:[heading('Local incident draft'),
        paragraph(DRAFT_STATUS[selected.draft_status] || 'This older incident needs a local draft.'),
        fields({problem_statement:selected.problem_statement || selected.packet?.problem || 'Local draft not yet available.',expected_outcome:selected.expected_outcome || selected.packet?.intended_outcome || 'Check the intended task outcome.'}),
        ['FAILED','UNAVAILABLE'].includes(selected.draft_status) && button('Generate local draft',()=>act('draft_incident'))]}),
      selected.state==='BLOCK_RETRIES' && jsxs('section',{style:box,children:[heading('1. Review the problem'),paragraph('Your local model drafts the problem and expected outcome. Check and edit these before preparing an Expert review.'),
        paragraph(DRAFT_STATUS[selected.draft_status] || 'This older incident needs a local draft.'),
        selected.draft_status==='READY' && paragraph(selected.draft_evidence==='detector_metadata_only'?'Only detector evidence was available. Task-specific details remain uncertain; check the intended outcome.':'Generated locally from the reported task and available evidence. It is a draft, not a verified diagnosis.'),
        selected.draft_status==='UNAVAILABLE' && paragraph('Set the local summary model in Guardian Agent settings. No cloud fallback is used.'),
        ['FAILED','UNAVAILABLE'].includes(selected.draft_status) && paragraph(selected.draft_error==='queue_full'?'The local drafting queue is full. Try again after current drafts finish.':'Check that the configured local model is running, then retry.'),
        (!selected.draft_status || ['PENDING','FAILED','UNAVAILABLE'].includes(selected.draft_status) || ['QUEUED','GENERATING'].includes(selected.draft_status) && Date.now()/1000-selected.draft_started_at>120) && button('Generate local draft',()=>act('draft_incident')),
        field('Problem to review',description,value=>{draftForm.current.problemDirty=true;setDescription(value)},true),field('What should success look like?',outcome,value=>{draftForm.current.outcomeDirty=true;setOutcome(value)},true),
        selected.draft_status==='READY' && button('Use generated draft',()=>{draftForm.current.problemDirty=false;draftForm.current.outcomeDirty=false;setDescription(selected.problem_statement || '');setOutcome(selected.expected_outcome || '')}),
        button('Prepare Expert review',()=>act('prepare',{description:description.trim(),outcome:outcome.trim()}),!description.trim() || !outcome.trim())]}),
      selected.state==='AWAIT_EGRESS_APPROVAL' && approval(selected,true),
      selected.state==='EXPERT_CONSULTATION' && paragraph('Expert is reviewing the approved summary. This page refreshes automatically.'),
      advice(selected),
      selected.state==='PROPOSED_FIX' && jsxs('section',{style:box,children:[heading('4. Review and approve one action'),paragraph('Expert advice grants no permission. Review the evidence, enter the exact action and define success. Hermes will also request its normal native approval.'),
        button('Ask Hermes to prepare the action',()=>continueChat('For the selected Guardian incident, compare Expert advice with local evidence and propose one exact corrective operation. Show the tool name, command or argument object, expected result and risks so I can review them in Guardian. Do not execute the operation before authorization.',{intent:'prepare_action',incident:selected.id})),
        field('Tool name',tool,setTool),field(tool==='terminal'?'Command to run':'Tool arguments (JSON object)',argumentsText,setArgumentsText,true),
        field('Success criteria',outcome,value=>{draftForm.current.outcomeDirty=true;setOutcome(value)},true),check('I checked this action against the evidence.',evidenceReviewed,setEvidenceReviewed),
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
      selected.state==='REVIEWED' && button('Continue with Hermes',()=>continueChat('Continue the selected incident’s Expert review. Compare the advice with local evidence and continue under normal approvals. Report success checks; my verification is still required.',{intent:'continue_review',review_id:selected.review_id})),
      (selected.outcome_unresolved || selected.state==='ESCALATE_TO_USER' && !selected.retry_ok) && jsxs('section',{style:box,children:[heading('Choose the next step'),paragraph(selected.outcome_unresolved?'The intended outcome has not been achieved. Keep this incident open and investigate the remaining problem. This does not grant another corrective attempt.':selected.retry_finished?'The corrective attempt did not succeed. This incident has no further corrective attempts available. Keep it open and investigate a different approach.':selected.expert_failure?'Expert review failed: '+readable(selected.expert_failure)+'. This incident remains open.':'Advice is inconclusive, more evidence is needed, or escalation was stopped. This incident remains open.'),
        paragraph('Ask Hermes to explain the evidence gaps and propose a different approach. This does not authorize another blocked operation or repeat consultation.'),
        button('Ask Hermes to investigate',()=>continueChat('The selected Guardian incident remains unresolved. Explain the evidence gaps and propose a different approach under current permissions. Do not repeat blocked actions, reset history or claim resolution.',{intent:'investigate',incident:selected.id}))]}),
      canVerify && jsxs('section',{style:box,children:[heading('5. Verify the result'),paragraph(selected.retry_ok?'The corrective tool reported success. Check the intended outcome before closing.':'Advice is available, but success has not been established. Check Hermes’s subsequent work before closing.'),
        paragraph('Success criteria: '+(selected.criteria || selected.packet?.intended_outcome || 'Record the checked outcome below.')),
        field('What did you check, and what was the result? (no secrets)',verification,setVerification,true),
        check('I verified the intended outcome was achieved.',verified,setVerified),
        button('Confirm resolved',()=>act('resolve',{verification:verification.trim()}),!verified || !verification.trim()),
        button('Still unresolved',()=>{setVerified(false);act('unresolved')})]}),
      selected.state==='DISMISSED' && jsxs('section',{style:box,children:[heading('Closed without review'),paragraph('You dismissed this incident. No successful fix was claimed.'),fields({reason:selected.dismissal_reason,closed:dated(selected.closed_at)})]}),
      selected.state==='RESOLVED' && jsxs('section',{style:box,children:[heading('Incident closed'),paragraph('You confirmed the outcome after checking the result.'),fields({problem:selected.packet?.problem || REASONS[selected.reason],success_criteria:selected.criteria || selected.packet?.intended_outcome || 'User verified outcome',verification:selected.verification || 'User verified corrective result'})]}),
      related.length>0 && jsxs('section',{children:[heading('Expert reviews for this incident'),...related.map(reviewCard)]}),
      details('Incident history',jsxs('div',{children:[jsx('ol',{children:[...(selected.transitions || []),...(selected.retry_finished?['Corrective attempt '+(selected.retry_ok?'reported success':'did not succeed')]:[]),...(selected.user_verified?['User verified outcome']:[])].map((event,index)=>jsx('li',{children:STATUS[event]?.[0] || readable(event)},index))}),fields({status:currentStatus[0],detected:dated(selected.time),attempts:selected.attempts || 0,success_criteria:selected.criteria || selected.packet?.intended_outcome || 'Not yet defined'})]}))]}),
      ]})
    ]}),
    details('Other Guardian tools',jsxs('div',{children:[
    loaded && details('Ask Expert · advice outside an incident',jsxs('div',{children:[paragraph('Use this for general task advice. These reviews do not close an incident.'),button('Request Expert advice',()=>act('request_review')),
      jsxs('label',{children:['Select a review',jsx('select',{style:inputStyle,value:review,onChange:e=>setReview(e.target.value),children:[jsx('option',{value:'',children:'Choose a review'}),...standalone.map(r=>jsx('option',{value:r.id,children:status(r)[0]+' · '+dated(r.time)+' · Review '+(standalone.indexOf(r)+1)},r.id))]})]}),
      reviewCard(selectedReview),!standalone.length && paragraph('No general advice requests in this chat.')]})),
    details('Advanced settings and maintenance',jsxs('div',{children:[paragraph('Expert provider/model, local summary model, conversation rounds and sending policy are configured in Hermes Agent settings and auxiliary models.'),
      button('Run local safeguard simulations (no cloud)',()=>act('test'),!session.trim()),
      button('Delete this chat’s Guardian history',()=>{if(window.confirm('Delete Guardian history for “'+selectedChatName+'” and release its incident blocks? This is maintenance, not incident resolution.'))act('reset')},!session.trim()),
      result?.simulation_only && details('Safeguard check results',fields({result:result.passed?'Passed':'Needs attention',checks:Array.isArray(result.checks)?result.checks.map(check=>check.name+' — '+(check.passed?'Passed':'Failed')):[]}))]}))
    ]}))
  ]})
}
export default {
  id:'hermes-expert-guardian',name:'Expert Guardian',
  register(ctx) {ctx.registerSettingsPage?.({id:'guardian',title:'Expert Guardian',icon:'shield',render:()=>jsx(Settings,{ctx})})}
}
