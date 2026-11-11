import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'

const source=fs.readFileSync(new URL('../desktop/plugin.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace('export default {','globalThis.plugin = {')
const pending=(id='review-1',hash='hash-1')=>({id,state:'AWAIT_SEND',packet_hash:hash,packet:{summary:{problem:'Public test failure'}},round:1})
function harness(reviews=[pending()],incidents=[]) {
  const states=[],calls=[],notifications=[],submissions=[]
  let cursor=0,rejectSend=false
  const ctx={rest:async(path,options)=>{
    calls.push({path,body:options?.body})
    if(path.startsWith('/incident'))return reviews===null?{incidents}:{incidents,reviews}
    if(options.body.action==='send_review'){
      if(rejectSend)throw Error('stale')
      return {state:'ADVICE_READY'}
    }
    return {simulation_only:true}
  }}
  const sandbox={host:{state:{focusedStoredSessionId:'session-1'},notify:n=>notifications.push(n),composer:{submit:(...args)=>{submissions.push(args);return true}}},
    useValue:v=>v,useState:initial=>{const i=cursor++;if(!(i in states))states[i]=initial;return [states[i],v=>{states[i]=v}]},
    jsx:(type,props)=>({type,props}),jsxs:(type,props)=>({type,props})}
  vm.createContext(sandbox)
  vm.runInContext(source+'\nglobalThis.renderSettings = Settings;',sandbox)
  const flatten=node=>node && typeof node==='object'?[node,...[node.props?.children].flat(Infinity).flatMap(flatten)]:[]
  const render=()=>{cursor=0;return flatten(sandbox.renderSettings({ctx}))}
  const button=text=>{const b=render().find(n=>n.type==='button'&&n.props.children===text);assert.ok(b,text);return b}
  const click=async text=>{const b=button(text);assert.equal(b.props.disabled,false,text+' disabled');await b.props.onClick()}
  const change=(label,value)=>{
    const node=render().find(n=>n.type==='label'&&n.props.children[0]===label)
    assert.ok(node,label);node.props.children[1].props.onChange({target:{value}})
  }
  return {render,button,click,change,calls,notifications,submissions,rejectSend:()=>{rejectSend=true}}
}
const approve='Approve reviewed summary and continue'
const refresh='Load / refresh reviews for this session'

{
  const h=harness()
  assert.equal(h.button(approve).props.disabled,true)
  await h.click(refresh)
  assert.equal(h.button(approve).props.disabled,false)
  const preview=h.render().find(n=>n.props['aria-label']==='Anonymous packet for approval')
  assert.ok(preview.props.children.includes('Public test failure'))
  await h.click('Run local safeguard simulations (no cloud)')
  assert.equal(h.button(approve).props.disabled,false,'Unrelated results must not erase the reviewed packet')
  await h.click(approve)
  const send=h.calls.find(c=>c.body?.action==='send_review').body
  assert.equal(send.session,'session-1');assert.equal(send.review_id,'review-1');assert.equal(send.packet_hash,'hash-1')
  assert.equal(h.submissions.length,1)
  assert.equal(h.button(approve).props.disabled,true,'Must not approve twice from a consumed snapshot')
}
{
  const h=harness([pending('one'),pending('two')])
  await h.click(refresh)
  assert.equal(h.button(approve).props.disabled,true,'Multiple pending reviews require explicit selection')
  h.change('Select a review','two')
  assert.equal(h.button(approve).props.disabled,false)
  h.change('Durable session ID (from the chat URL)','another-session')
  assert.equal(h.button(approve).props.disabled,true,'Snapshots are bound to the loaded session')
  assert.equal(h.render().some(n=>n.props['aria-label']==='Anonymous packet for approval'),false)
}
{
  const h=harness()
  h.change('Review ID (from request or review history)',' review-1 ')
  await h.click(refresh)
  assert.equal(h.button(approve).props.disabled,false,'Pasted review IDs are trimmed')
  h.rejectSend();await h.click(approve)
  assert.equal(h.button(approve).props.disabled,true)
  assert.equal(h.submissions.length,0)
  assert.ok(h.notifications.at(-1).message.includes('Reload reviews'))
}
{
  const h=harness(null)
  await h.click(refresh)
  assert.equal(h.button(approve).props.disabled,true)
  assert.ok(h.notifications.some(n=>n.message.includes('Restart Hermes')))
}
{
  const h=harness([{...pending(),state:'ADVICE_READY'}])
  h.change('Review ID (from request or review history)','review-1')
  await h.click(refresh)
  assert.equal(h.button(approve).props.disabled,true,'Only AWAIT_SEND may be approved')
}
console.log('Frontend review selection, preview, session binding and approval checks passed')
{
  const incidents=[
    {id:'incident-one',reason:'identical_failure',state:'AWAIT_EGRESS_APPROVAL',packet_hash:'incident-hash',packet:{problem:'First incident'}},
    {id:'incident-two',reason:'no_progress',state:'BLOCK_RETRIES'}
  ]
  const h=harness([],incidents)
  await h.click('Refresh incidents')
  assert.equal(h.button('Approve sending preview to Expert').props.disabled,true)
  h.change('Select an incident','incident-one')
  assert.equal(h.button('Approve sending preview to Expert').props.disabled,false)
  const preview=h.render().find(n=>n.props['aria-label']==='Incident packet for approval')
  assert.ok(preview.props.children.includes('First incident'))
  await h.click('Run local safeguard simulations (no cloud)')
  assert.equal(h.button('Approve sending preview to Expert').props.disabled,false)
  await h.click('Approve sending preview to Expert')
  const send=h.calls.find(c=>c.body?.action==='send').body
  assert.equal(send.incident,'incident-one');assert.equal(send.packet_hash,'incident-hash')
  h.change('Select an incident','incident-two')
  assert.equal(h.button('Approve sending preview to Expert').props.disabled,true)
  h.change('Durable session ID (from the chat URL)','another-session')
  assert.equal(h.render().some(n=>n.type==='label'&&n.props.children[0]==='Select an incident'),false)
}
{
  const h=harness([],[{id:'only-active',reason:'identical_failure',state:'BLOCK_RETRIES'},
                      {id:'old',reason:'no_progress',state:'RESOLVED'}])
  await h.click('Refresh incidents')
  const selector=h.render().find(n=>n.type==='label'&&n.props.children[0]==='Select an incident')
  assert.equal(selector.props.children[1].props.value,'only-active')
}
console.log('Incident selection, packet binding and session isolation checks passed')
