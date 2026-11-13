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
  const ctx={rest:async(path,options)=>{
    calls.push({path,body:options?.body})
    if(path.startsWith('/incident')) {
      if(deferredLoad){const next=deferredLoad;deferredLoad=null;return next}
      if(rejectLoad)throw Error('offline')
      return reviews===null?{incidents}:{incidents:structuredClone(incidents),reviews:structuredClone(reviews),mode}
    }
    const body=options.body
    const i=incidents.find(i=>i.id===body.incident),r=reviews?.find(r=>r.id===body.review_id)
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
  const sandbox={host:{state:{focusedStoredSessionId:'session-1'},notify:n=>notifications.push(n),composer:{submit:(...args)=>{submissions.push(args);return acceptComposer}}},
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
  return {render,button,click,change,check,calls,notifications,submissions,text,settle,tree:()=>{render();return tree},
    start:async()=>{await settle()},tick:async()=>{await Promise.all([...timers.values()].map(fn=>fn()));await settle()},
    setIncidents:items=>{incidents=structuredClone(items)},rejectSend:()=>{rejectSend=true},rejectLoad:()=>{rejectLoad=true},
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
  assert.equal(h.render().find(n=>n.type==='select').props.value,'two')
  await h.change('Durable session ID (from the chat URL)','another-session')
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
  await h.click('Open incident')
  assert.equal(h.render().find(n=>n.type==='textarea').props.value,'','Drafts do not leak across incident selections')
}
{
  const h=harness();await h.start();h.rejectComposer();await h.click('Approve summary and get advice')
  assert.ok(h.text().includes('Open this chat'))
}
{
  const h=harness([],[incident()]);await h.start();h.rejectLoad();await h.click('Reload incidents and reviews')
  assert.ok(h.text().includes('Could not load'));assert.ok(!h.text().includes('Prepare Expert review'))
}
// A slow response from another chat must not overwrite the current chat.
{
  const h=harness([],[incident()]);await h.start()
  let release;h.deferLoad(new Promise(resolve=>{release=resolve}))
  const old=h.button('Reload incidents and reviews').props.onClick()
  await h.change('Durable session ID (from the chat URL)','new-chat')
  release({incidents:[incident('AWAIT_EGRESS_APPROVAL',{packet:{problem:'Stale private preview'},packet_hash:'old'})],reviews:[]})
  await old;await h.settle();assert.ok(!h.text().includes('Stale private preview'))
}
// General advice stays accessible when this chat also has an open incident.
{
  const h=harness([pending()],[incident()]);await h.start()
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
  const old=h.button('Reload incidents and reviews').props.onClick()
  await h.tick()
  fail(Error('old request failed'));await old;await h.settle()
  assert.ok(h.text().includes('Prepare Expert review'))
  assert.ok(!h.text().includes('Could not load'))
}

console.log('Frontend checks passed: guided recovery, advisory linkage, verification, failures, polling, session isolation and exact approvals')
