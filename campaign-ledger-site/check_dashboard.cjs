// Checks the actual public UI script against a minimal DOM; not browser layout QA.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/dist/index.html','utf8');
const payload=html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
const ids=new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
class Element {constructor(tag){this.tag=tag;this.children=[];this.events={};this.style={};this.textContent='';this.value='';this.hidden=false;this.attrs={};this.dataset={};this.classList={toggle(){}};} append(...els){this.children.push(...els)} replaceChildren(...els){this.children=els} setAttribute(k,v){this.attrs[k]=v} addEventListener(k,fn){this.events[k]=fn} click(){this.clicked=true} get valueAsNumber(){return this.value===''?NaN:Number(this.value)} checkValidity(){return Number.isFinite(this.valueAsNumber)&&this.valueAsNumber>=0&&this.valueAsNumber<=this.max}}
const nodes=new Map(),tabs=['report','audiences','runbook'].map(view=>{const e=new Element('button');e.dataset.view=view;return e});
const document={getElementById(id){assert.ok(ids.has(id),'Missing real HTML element '+id);if(!nodes.has(id))nodes.set(id,new Element('div'));return nodes.get(id)},createElement(tag){return new Element(tag)},querySelectorAll(){return tabs}};
const get=id=>document.getElementById(id);get('report-data').textContent=payload;
for(const [id,value] of [['channel','All'],['window','all'],['scenario','success'],['segment','first'],['audience-channel','All']])get(id).value=value;
for(const [id,value,max] of [['aov','120',10000],['frequency','3',100],['lifespan','2',50]]){get(id).value=value;get(id).max=max}
let csvBlob;const context=vm.createContext({document,Intl,JSON,Number,Math,Blob,URL:{createObjectURL(b){csvBlob=b;return 'blob:test'},revokeObjectURL(){}},setTimeout(fn){fn()}});
vm.runInContext(script,context);
const data=JSON.parse(payload),sum=(scenario,key)=>data[scenario].report.windows.all.rows.reduce((s,r)=>s+r[key],0);
assert.equal(get('rows').children.length,4);assert.equal(get('spend').textContent,'$9,257.18');assert.equal(get('ltv').textContent,'$720.00');assert.equal(get('audience-count').textContent,'181 sample customers');
get('scenario').value='failure';get('run').events.click();assert.equal(get('spend').textContent,'$9,257.18');assert.ok(get('run-notice').textContent.includes('failed'));assert.equal(get('sources').children.length,3);get('create-brief').events.click();assert.ok(get('brief').textContent.includes('DATA ISSUE'));
get('scenario').value='correction';get('run').events.click();assert.equal(get('spend').textContent,'$9,307.18');assert.ok(sum('correction','refund_cents')>sum('success','refund_cents'));get('run').events.click();assert.equal(get('spend').textContent,'$9,307.18');
get('channel').value='Google';get('channel').events.change();assert.equal(get('rows').children.length,2);get('create-brief').events.click();assert.ok(!get('brief').textContent.includes('meta_prospect'));get('window').value='current';get('window').events.change();assert.ok(get('brief').textContent.includes('Filters changed'));
get('segment').value='repeat';get('segment').events.change();get('audience-channel').value='Google';get('audience-channel').events.change();assert.equal(get('audience-count').textContent,'16 sample customers');
tabs[1].events.click();assert.equal(get('view-report').hidden,true);assert.equal(get('view-audiences').hidden,false);assert.equal(tabs[1].attrs['aria-pressed'],'true');
get('aov').value='';get('aov').events.input();assert.equal(get('ltv').textContent,'Enter valid assumptions');
(async()=>{get('download').events.click();const report=await csvBlob.text();assert.equal(report.split('\r\n').length,3);assert.ok(report.includes('net_revenue_cents'));assert.ok(!report.includes('Meta'));get('export-audience').events.click();const audience=await csvBlob.text();assert.equal(audience.split('\r\n').length,17);assert.ok(audience.includes('Google'));console.log('UI checks passed: scenarios, retained data, corrections, filters, tabs, briefs, audience export, and LTV validation.')})().catch(e=>{console.error(e);process.exitCode=1});
