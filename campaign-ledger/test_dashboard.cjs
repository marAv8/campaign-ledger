// Execute the dashboard's actual inline script against a minimal local DOM.
// Checks calculation and event behavior; this is not a browser layout test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/output/index.html','utf8');
const payload=html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(tag){this.tag=tag;this.children=[];this.events={};this.style={};this.textContent='';this.value='';}append(...els){this.children.push(...els);}replaceChildren(...els){this.children=els;}setAttribute(){}addEventListener(name,fn){this.events[name]=fn;}checkValidity(){const n=this.valueAsNumber;return Number.isFinite(n)&&n>=0&&n<=this.max;}get valueAsNumber(){return this.value===''?NaN:Number(this.value);}click(){this.clicked=true;}}
const nodes=new Map();const document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Element('div'));return nodes.get(id);},createElement(tag){return new Element(tag);}};
const get=id=>document.getElementById(id);get('report-data').textContent=payload;get('channel').value='All';get('window').value='all';
for(const [id,value,max] of [['aov','120',10000],['frequency','3',100],['lifespan','2',50]]){get(id).value=value;get(id).max=max;}
let csvBlob;const context=vm.createContext({document,Intl,JSON,Number,Math,Blob,URL:{createObjectURL(blob){csvBlob=blob;return 'blob:test';},revokeObjectURL(){}},setTimeout(fn){fn();}});
vm.runInContext(script,context);
assert.equal(get('rows').children.length,4);assert.equal(get('spend').textContent,'$9,257.18');assert.equal(get('cac').textContent,'$48.89');assert.equal(get('roas').textContent,'2.94×');assert.equal(get('ltv').textContent,'$720.00');
get('channel').value='Meta';get('channel').events.change();assert.equal(get('rows').children.length,2);
get('window').value='current';get('window').events.change();const data=JSON.parse(payload);const rows=data.windows.current.rows.filter(r=>r.channel==='Meta');const expected=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(rows.reduce((sum,r)=>sum+r.ad_spend_cents+r.other_acquisition_cents,0)/100/rows.reduce((sum,r)=>sum+r.new_customers,0));assert.equal(get('cac').textContent,expected);
get('aov').value='100';get('aov').events.input();assert.equal(get('ltv').textContent,'$600.00');get('aov').value='';get('aov').events.input();assert.equal(get('ltv').textContent,'Enter valid assumptions');
get('channel').value='Google';get('channel').events.change();assert.equal(get('alerts').children[0].textContent,'No changes crossed the comparison thresholds.');
get('download').events.click();csvBlob.text().then(csv=>{assert.equal(csv.split('\r\n').length,3);assert.ok(csv.includes('Google'));assert.ok(!csv.includes('Meta'));console.log('Dashboard script checks passed: totals, filters, LTV validation, alerts, and CSV export.');});
