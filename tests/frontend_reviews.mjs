import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'

const source=fs.readFileSync(new URL('../desktop/plugin.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace('export default {','globalThis.plugin = {')
export const pending=(id='review-1',hash='hash-1')=>({id,state:'AWAIT_SEND',packet_hash:hash,packet:{summary:{problem:'Public test failure'}},round:1})
export const incident=(state='BLOCK_RETRIES',extra={})=>({id:'incident-1',reason:'identical_failure',state,attempts:2,transitions:['LOOP_CONFIRMED',state],...extra})
export function harness(initialReviews=[pending()],initialIncidents=[],mode='enforce') {
  const states=[],calls=[],notifications=[],submissions=[],effects=[],timers=new Map()
  let cursor=0,tree,rejectSend=false,acceptComposer=true,rejectLoad=false,dirty=false,timerId=0
  let reviews=structuredClone(initialReviews),incidents=structuredClone(initialIncidents),deferredLoad=null
  const otherChats=new Map()
  let chats=[{id:'session-1',title:'Fix the package installation'},{id:'another-session',title:'Plan the weekly report'},{id:'new-chat',title:'Investigate the new issue'}],rejectNames=false,deferredNames=null
  const ctx={rest:async(path,options)=>{
    calls.push({path,body:options?.body})
    if(path==='/incidents')return {sessions:[{session:'session-1',incidents:structuredClone(incidents)},...[...otherChats].map(([session,data])=>({session,incidents:structuredClone(data.incidents)}))]}
    if(path.startsWith('/incident?')) {
      if(deferredLoad){const next=deferredLoad;deferredLoad=null;return next}
      if(rejectLoad)throw Error('offline')
      const target=decodeURIComponent(path.split('session=')[1]),data=otherChats.get(target)
      return data?{...structuredClone(data),mode}:reviews===null?{incidents}:{incidents:structuredClone(incidents),reviews:structuredClone(reviews),mode}
    }
    const body=options.body
    const data=otherChats.get(body.session)
    const i=(data?.incidents || incidents).find(i=>i.id===body.incident),r=(data?.reviews || reviews)?.find(r=>r.id===body.review_id)
    switch(body.action){
      case 'send_review': if(rejectSend)throw Error('stale');r.state='ADVICE_READY';return {state:'ADVICE_READY'}
      case 'cancel_review': r.state='CANCELLED';break
      case 'request_review': reviews.push({id:'new-review',state:'REQUESTED'});return {review_id:'new-review'}
      case 'prepare': i.state='AWAIT_EGRESS_APPROVAL';i.packet={problem:body.description,intended_outcome:body.outcome};i.packet_hash='incident-hash';break
      case 'send': if(rejectSend)throw Error('stale');i.state='PROPOSED_FIX';i.advice={root_cause:'Test cause',recommended_corrective_action:'Check the fixture'};break
      case 'authorize': i.state='SINGLE_RETRY';i.criteria=body.criteria;break
      case 'resolve': i.state='RESOLVED';i.user_verified=true;i.verification=body.verification;break
      case 'unresolved': i.outcome_unresolved=true;break
      case 'reset': incidents=[];reviews=[];break
      case 'test': return {passed:true,simulation_only:true}
    }
    return {ok:true}
  }}
  const sandbox={host:{state:{focusedStoredSessionId:'session-1',profile:'default',focusedSessionProfile:'default',viewport:{narrow:false,width:1280}},request:async(method,params)=>{calls.push({method,params});if(deferredNames){const value=deferredNames;deferredNames=null;return value}if(rejectNames)throw Error('offline');return {sessions:structuredClone(chats)}},notify:n=>notifications.push(n),composer:{submit:(...args)=>{submissions.push(args);return acceptComposer}}},
    useValue:v=>v,useState:initial=>{const i=cursor++;if(!(i in states))states[i]=initial;return [states[i],v=>{states[i]=typeof v==='function'?v(states[i]):v;dirty=true}]},
    useRef:initial=>{const i=cursor++;if(!(i in states))states[i]={current:initial};return states[i]},
    useEffect:(fn,deps)=>{const i=cursor++,previous=states[i];if(!previous || deps.some((v,index)=>!Object.is(v,previous.deps[index]))){states[i]={deps,cleanup:previous?.cleanup};effects.push(()=>{states[i].cleanup?.();states[i].cleanup=fn()})}},
    setInterval:fn=>{const id=++timerId;timers.set(id,fn);return id},clearInterval:id=>timers.delete(id),window:{confirm:()=>true},
    jsx:(type,props)=>({type,props}),jsxs:(type,props)=>({type,props})}
  vm.createContext(sandbox)
  vm.runInContext(source+'\nglobalThis.renderSettings = Settings;',sandbox)
  const flatten=node=>node && typeof node==='object'?[node,...[node.props?.children].flat(Infinity).flatMap(flatten)]:[]
  const render=()=>{cursor=0;tree=sandbox.renderSettings({ctx});return flatten(tree)}
  const settle=async()=>{for(let round=0;round<12;round++){dirty=false;render();while(effects.length)effects.shift()();await new Promise(resolve=>setImmediate(resolve));if(!dirty&&!effects.length)break}render()}
  const button=text=>{const b=render().find(n=>n.type==='button'&&n.props.children===text);assert.ok(b,text);return b}
  const click=async text=>{const b=button(text);assert.equal(b.props.disabled,false,text+' disabled');await b.props.onClick();await settle()}
  const change=async(label,value)=>{
    const node=render().find(n=>n.type==='label'&&n.props.children[0]===label)
    assert.ok(node,label);node.props.children[1].props.onChange({target:{value}});await settle()
  }
  const check=async(label,value=true)=>{const node=render().find(n=>n.type==='label'&&n.props.children[1]===' '+label);assert.ok(node,label);node.props.children[0].props.onChange({target:{checked:value}});await settle()}
  const text=()=>render().flatMap(n=>[n.props?.children].flat(Infinity).filter(c=>typeof c==='string')).join('\n')
  const chooseChatIncident=async(target,id)=>{
    const chat=render().find(n=>n.type==='button'&&n.props.role==='treeitem'&&n.props.value===target&&'aria-expanded' in n.props)
    assert.ok(chat,'Chat exists in tree');if(!chat.props['aria-expanded']){chat.props.onClick();await settle()}
    const item=render().find(n=>n.type==='button'&&n.props.role==='treeitem'&&n.props.value===id&&'aria-selected' in n.props)
    assert.ok(item,'Incident exists under expanded chat');item.props.onClick();await settle()
  }
  return {render,button,click,change,check,calls,notifications,submissions,text,settle,tree:()=>{render();return tree},
    start:async(autoSelect=true)=>{await settle();if(autoSelect){const item=render().find(n=>n.type==='button'&&n.props.role==='treeitem'&&'aria-selected' in n.props);if(item){item.props.onClick();await settle()}}},chooseChatIncident,setChatIncidents:(target,items,advice=[])=>otherChats.set(target,{incidents:structuredClone(items),reviews:structuredClone(advice)}),tick:async()=>{await Promise.all([...timers.values()].map(fn=>fn()));await settle()},
    setIncidents:items=>{incidents=structuredClone(items)},rejectSend:()=>{rejectSend=true},rejectLoad:()=>{rejectLoad=true},
    setChats:items=>{chats=structuredClone(items)},rejectNames:()=>{rejectNames=true},deferNames:promise=>{deferredNames=promise},
    rejectComposer:()=>{acceptComposer=false},deferLoad:promise=>{deferredLoad=promise}}
}

// General review approval remains tied to the loaded session and exact packet hash.
{
  const h=harness();await h.start()
  assert.equal(h.button('Approve summary and get advice').props.disabled,false)
  assert.ok(h.text().includes('Public test failure'))
  await h.click('Run local safeguard simulations (no cloud)')
  assert.equal(h.button('Approve summary and get advice').props.disabled,false)
  await h.click('Approve summary and get advice')
  const send=h.calls.find(c=>c.body?.action==='send_review').body
  assert.equal(send.session,'session-1');assert.equal(send.review_id,'review-1');assert.equal(send.packet_hash,'hash-1')
  assert.equal(h.submissions.length,1)
  assert.ok(!h.render().some(n=>n.type==='button'&&n.props.children==='Approve summary and get advice'))
}
{
  const h=harness([pending('one'),pending('two')]);await h.start()
  assert.ok(!h.text().includes('Public test failure'),'Multiple reviews require explicit choice')
  await h.change('Select a review','two')
  assert.equal(h.button('Approve summary and get advice').props.disabled,false)
  assert.equal(h.render().find(n=>n.type==='label'&&n.props.children[0]==='Select a review').props.children[1].props.value,'two')
  h.setChatIncidents('another-session',[incident('BLOCK_RETRIES',{id:'other-incident'})]);await h.click('Refresh tree');await h.chooseChatIncident('another-session','other-incident')
  assert.ok(!h.text().includes('Public test failure'),'Old selected review is cleared on session change')
}
{
  const h=harness();await h.start();h.rejectSend();await h.click('Approve summary and get advice')
  assert.equal(h.submissions.length,0)
  assert.ok(h.text().includes('could not be completed'))
  assert.ok(!h.text().includes('Public test failure'),'Rejected approval invalidates the snapshot')
}
{
  const h=harness(null);await h.start();assert.ok(h.text().includes('Restart Hermes'))
}
// Walk the entire legacy recovery journey. Irrelevant future actions are absent.
{
  const h=harness([],[incident()]);await h.start()
  assert.ok(h.text().includes('Review the problem'))
  assert.equal(h.button('Prepare Expert review').props.disabled,true)
  assert.ok(!h.text().includes('Approve one corrective attempt'))
  await h.change('Problem to review','Public fixture cannot be read')
  await h.change('What should success look like?','Fixture read succeeds')
  await h.click('Prepare Expert review')
  assert.ok(h.text().includes('Public fixture cannot be read'))
  await h.click('Approve summary and get advice')
  assert.ok(h.text().includes('Test cause'))
  assert.equal(h.button('Approve one corrective attempt').props.disabled,true)
  await h.change('Command to run','echo checked')
  await h.check('I checked this action against the evidence.')
  await h.click('Approve one corrective attempt')
  const authorize=h.calls.find(c=>c.body?.action==='authorize').body
  assert.equal(authorize.tool,'terminal');assert.equal(authorize.args.command,'echo checked')
  assert.equal(authorize.criteria,'Fixture read succeeds');assert.equal(authorize.evidence_reviewed,true)
  assert.ok(h.submissions.at(-1)[1].includes('echo checked'))
  assert.ok(!h.text().includes('Confirm resolved'),'Authorization does not imply success')
  h.setIncidents([incident('ESCALATE_TO_USER',{retry_finished:true,retry_ok:true,criteria:'Fixture read succeeds'})]);await h.tick()
  assert.equal(h.button('Confirm resolved').props.disabled,true)
  await h.change('What did you check, and what was the result? (no secrets)','Read succeeded with the expected fixture content')
  await h.check('I verified the intended outcome was achieved.')
  await h.click('Confirm resolved')
  assert.ok(h.text().includes('Incident closed'))
  assert.ok(h.text().includes('Read succeeded with the expected fixture content'))
}
// Advisory consultations stay inside their incident and never imply resolution.
{
  const h=harness([{...pending(),incident:'incident-1'}],[incident('BLOCK_RETRIES')]);await h.start()
  assert.ok(h.text().includes('Expert reviews for this incident'))
  await h.click('Approve summary and get advice')
  assert.equal(h.calls.find(c=>c.body?.action==='send_review').body.review_id,'review-1')
  h.setIncidents([incident('REVIEWED',{review_id:'review-1'})]);await h.tick()
  assert.ok(h.text().includes('outcome not verified'))
  await h.click('Still unresolved')
  assert.ok(h.text().includes('Outcome still unresolved'))
  assert.equal(h.button('Confirm resolved').props.disabled,true)
}
{
  const h=harness([],[incident('ESCALATE_TO_USER',{retry_finished:true,retry_ok:false})]);await h.start()
  assert.ok(h.text().includes('did not succeed'))
  assert.ok(!h.text().includes('Confirm resolved'))
  assert.ok(!h.text().includes('Approve one corrective attempt'))
}
{
  const h=harness([],[incident('ESCALATE_TO_USER',{expert_failure:'timeout'})]);await h.start()
  assert.ok(h.text().includes('Expert review failed: Timeout'))
  await h.click('Ask Hermes to investigate');assert.ok(h.submissions[0][1].includes('Do not repeat blocked actions'))
}
{
  const h=harness([],[incident('PROPOSED_FIX')],'monitor');await h.start()
  assert.equal(h.button('Approve one corrective attempt').props.disabled,true)
  assert.ok(h.text().includes('requires Enforce mode'))
}
{
  const h=harness([],[incident('PROPOSED_FIX')]);await h.start()
  await h.change('Tool name','read_file');await h.change('Tool arguments (JSON object)','[]')
  await h.change('Success criteria','Read succeeds');await h.check('I checked this action against the evidence.')
  await h.click('Approve one corrective attempt')
  assert.ok(h.text().includes('valid JSON object'));assert.ok(!h.calls.some(c=>c.body?.action==='authorize'))
}
{
  const h=harness([],[incident(),incident('RESOLVED',{id:'old'})]);await h.start()
  assert.ok(h.text().includes('Prepare Expert review'),'Sole open incident is selected ahead of closed history')
  await h.change('Problem to review','Draft from first incident')
  h.setIncidents([incident(),incident('BLOCK_RETRIES',{id:'second'})]);await h.tick()
  await h.chooseChatIncident('session-1','second')
  assert.equal(h.render().find(n=>n.type==='label'&&n.props.children[0]==='Problem to review').props.children[1].props.value,'','Drafts do not leak across incident selections')
}
{
  const h=harness();await h.start();h.rejectComposer();await h.click('Approve summary and get advice')
  assert.ok(h.text().includes('Open “Fix the package installation”'))
}
{
  const h=harness([],[incident()]);await h.start();h.rejectLoad();await h.click('Reload incident')
  assert.ok(h.text().includes('Could not load'));assert.ok(!h.text().includes('Prepare Expert review'))
}
// A slow response from another chat must not overwrite the current chat.
{
  const h=harness([],[incident()]);await h.start()
  h.setChatIncidents('new-chat',[incident('BLOCK_RETRIES',{id:'new-incident'})]);await h.click('Refresh tree')
  let release;h.deferLoad(new Promise(resolve=>{release=resolve}))
  const old=h.button('Reload incident').props.onClick()
  await h.chooseChatIncident('new-chat','new-incident')
  release({incidents:[incident('AWAIT_EGRESS_APPROVAL',{packet:{problem:'Stale private preview'},packet_hash:'old'})],reviews:[]})
  await old;await h.settle();assert.ok(!h.text().includes('Stale private preview'))
}
// General advice stays accessible when this chat also has an open incident.
{
  const h=harness([pending()],[incident()]);await h.start();await h.change('Select a review','review-1')
  assert.ok(h.text().includes('Prepare Expert review'))
  assert.ok(h.text().includes('Public test failure'))
  await h.click('Approve summary and get advice')
  assert.equal(h.calls.find(c=>c.body?.action==='send_review').body.review_id,'review-1')
  assert.ok(h.text().includes('Prepare Expert review'),'General advice does not advance the unrelated incident')
}
// A late failed load must not erase a newer, successful load for the same chat.
{
  const h=harness([],[incident()]);await h.start()
  let fail;h.deferLoad(new Promise((_,reject)=>{fail=reject}))
  const old=h.button('Reload incident').props.onClick()
  await h.tick()
  fail(Error('old request failed'));await old;await h.settle()
  assert.ok(h.text().includes('Prepare Expert review'))
  assert.ok(!h.text().includes('Could not load'))
}

// Every visible component uses readable labels, including expanded history and results.
{
  const h=harness([{...pending('opaque-review-identifier'),time:123}],[incident('REVIEWED',{id:'opaque-incident-identifier',review_id:'opaque-review-identifier',packet_hash:'opaque-packet-hash',scope:'opaque-scope-digest'})]);await h.start()
  assert.ok(h.text().includes('Chat: Fix the package installation'))
  for(const raw of ['session-1','opaque-review-identifier','opaque-incident-identifier','opaque-packet-hash','opaque-scope-digest','REVIEWED'])assert.ok(!h.text().includes(raw),'Internal value leaked: '+raw)
  assert.ok(!h.text().includes('Durable session ID'))
  await h.click('Run local safeguard simulations (no cloud)')
  assert.ok(!h.text().includes('opaque-'))
}
// Duplicate names and unnamed chats remain selectable without displaying an ID.
{
  const h=harness([],[incident()]);h.setChatIncidents('another-session',[incident('BLOCK_RETRIES',{id:'duplicate-incident'})]);h.setChatIncidents('new-chat',[incident('REVIEWED',{id:'untitled-incident'})]);h.setChats([{id:'session-1',title:'Weekly review',started_at:123},{id:'another-session',title:'Weekly review',started_at:123},{id:'new-chat',title:'',preview:''}]);await h.start()
  const options=h.render().filter(n=>n.type==='button'&&n.props.role==='treeitem'&&'aria-expanded' in n.props)
  assert.ok(options.some(n=>n.props.children.includes('Chat 1')))
  assert.ok(options.some(n=>n.props.children.includes('Chat 2')))
  assert.ok(options.some(n=>n.props.children.includes('Untitled chat')))
  h.setChatIncidents('another-session',[incident('BLOCK_RETRIES',{id:'other-incident'})]);await h.click('Refresh tree');await h.chooseChatIncident('another-session','other-incident')
  assert.ok(h.text().includes('Chat: Weekly review'))
  assert.ok(h.calls.some(c=>c.path==='/incident?session=another-session'),'Names must not replace the internal routing key')
}
// Renamed chats refresh; failed name lookup never falls back to the raw key.
{
  const h=harness([],[incident()]);await h.start();h.setChats([{id:'session-1',title:'Renamed task chat'}]);await h.tick()
  assert.ok(h.text().includes('Chat: Renamed task chat'))
  h.rejectNames();await h.click('Refresh tree')
  assert.ok(h.text().includes('Chat names could not be loaded'))
  assert.ok(!h.text().includes('session-1'))
}
// User-visible composer messages omit routing keys; selected routing travels in the API.
{
  const h=harness([{...pending(),state:'ADVICE_READY',delivered:true}]);await h.start();await h.change('Select a review','review-1')
  await h.click('Continue with Hermes')
  assert.ok(!h.submissions[0][1].includes('review-1'))
  assert.equal(h.calls.find(c=>c.body?.action==='handoff').body.review_id,'review-1')
}

// The workspace opens without an implicitly selected incident or an approval.
{
  const h=harness([],[incident()]);await h.start(false)
  assert.ok(h.text().includes('Select an incident'))
  assert.ok(!h.text().includes('Prepare Expert review'))
  const workspace=h.render().find(n=>n.props['aria-label']==='Incident workspace')
  assert.equal(workspace.props.style.display,'grid')
  assert.ok(workspace.props.style.gridTemplateColumns.includes('32%'))
  assert.ok(h.render().some(n=>n.type==='aside'&&n.props['aria-label']==='Chats and incidents'))
  await h.chooseChatIncident('session-1','incident-1')
  assert.ok(h.text().includes('Step 1 of 6'))
  assert.ok(h.text().includes('Who acts next: You'))
  assert.ok(h.text().includes('Prepare Expert review'))
  assert.equal(h.calls.some(c=>c.body?.action),false,'Selection is read-only')
}
// A different chat expands independently; selecting its child loads only that incident.
{
  const h=harness([],[incident('AWAIT_EGRESS_APPROVAL',{packet:{problem:'First chat preview'},packet_hash:'first-hash'})])
  h.setChatIncidents('another-session',[incident('AWAIT_EGRESS_APPROVAL',{id:'other-incident',packet:{problem:'Second chat preview'},packet_hash:'second-hash'})])
  await h.start(false)
  await h.chooseChatIncident('another-session','other-incident')
  assert.ok(h.text().includes('Second chat preview'))
  assert.ok(!h.text().includes('First chat preview'))
  await h.click('Approve summary and get advice')
  const send=h.calls.find(c=>c.body?.action==='send').body
  assert.equal(send.session,'another-session');assert.equal(send.incident,'other-incident');assert.equal(send.packet_hash,'second-hash')
  const treeItem=h.render().find(n=>n.props.role==='treeitem'&&n.props.value==='other-incident')
  assert.equal(treeItem.props['aria-selected'],true)
}
// Clicking between incidents clears drafts and approvals, and refreshing retains the selection.
{
  const h=harness([],[incident(),incident('PROPOSED_FIX',{id:'second'})]);await h.start()
  await h.change('Problem to review','Draft for first incident')
  await h.chooseChatIncident('session-1','second')
  assert.ok(!h.text().includes('Draft for first incident'))
  assert.equal(h.button('Approve one corrective attempt').props.disabled,true)
  await h.tick()
  assert.ok(h.render().some(n=>n.props.role==='treeitem'&&n.props.value==='second'&&n.props['aria-selected']))
}
// A compressed chat groups both lineage records and routes the selected incident to its owner.
{
  const h=harness([]);h.setChats([{id:'tip-chat',_lineage_root_id:'session-1',title:'Long-running task'}])
  h.setChatIncidents('tip-chat',[incident('BLOCK_RETRIES',{id:'tip-incident'})])
  h.setIncidents([incident('BLOCK_RETRIES',{id:'root-incident'})]);await h.start(false)
  const chat=h.render().find(n=>n.props.role==='treeitem'&&'aria-expanded' in n.props)
  assert.equal(chat.props['aria-expanded'],true)
  assert.ok(chat.props.children.includes('(2)'))
  h.render().find(n=>n.props.role==='treeitem'&&n.props.value==='tip-incident').props.onClick();await h.settle()
  assert.ok(h.calls.some(c=>c.path==='/incident?session=tip-chat'))
  assert.ok(h.text().includes('Chat: Long-running task'))
  h.render().find(n=>n.props.role==='treeitem'&&'aria-expanded' in n.props).props.onClick();await h.settle()
  assert.ok(!h.render().some(n=>n.props.role==='treeitem'&&n.props.value==='root-incident'),'A lineage chat can be collapsed')
}


// Only chats with unresolved incidents appear, including reviewed-but-unverified work.
{
  const h=harness([],[incident('RESOLVED')]);
  h.setChatIncidents('another-session',[incident('REVIEWED',{id:'unverified'})]);await h.start(false)
  const chatKeys=h.render().filter(n=>n.props.role==='treeitem'&&'aria-expanded' in n.props).map(n=>n.props.value)
  assert.deepEqual(chatKeys,['another-session'])
  assert.equal(h.button('Use focused chat').props.disabled,true)
}
// Completing the last incident removes its chat while leaving the closure confirmation visible.
{
  const h=harness([],[incident('ESCALATE_TO_USER',{retry_ok:true})]);await h.start()
  await h.change('What did you check, and what was the result? (no secrets)','Expected result confirmed')
  await h.check('I verified the intended outcome was achieved.');await h.click('Confirm resolved')
  assert.ok(h.text().includes('Incident closed'))
  assert.ok(h.text().includes('No chats with open incidents.'))
  assert.ok(!h.render().some(n=>n.props.role==='treeitem'&&'aria-expanded' in n.props))
}
// Background refresh removes closed-only chats and adds newly open ones.
{
  const h=harness([],[incident()]);await h.start(false)
  h.setIncidents([incident('RESOLVED')]);h.setChatIncidents('new-chat',[incident('BLOCK_RETRIES',{id:'new-open'})]);await h.tick()
  const chatKeys=h.render().filter(n=>n.props.role==='treeitem'&&'aria-expanded' in n.props).map(n=>n.props.value)
  assert.deepEqual(chatKeys,['new-chat'])
}
console.log('Frontend checks passed: open-incident chat filtering, closure and refresh, tree selection, names and approval isolation')
