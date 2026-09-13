const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/xlsx.min-DAEdtGqP.js","assets/vendor-DkcvSUHc.js","assets/vendor-DULRuONn.css"])))=>i.map(i=>d[i]);
import{c as p,_ as y}from"./index-e-4jkkFI.js";/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const x=[["path",{d:"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",key:"169zse"}]],F=p("activity",x);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const g=[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16",key:"c24i48"}],["path",{d:"m19 9-5 5-4-4-3 3",key:"2osh9i"}]],N=p("chart-line",g);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const k=[["path",{d:"M5 21v-6",key:"1hz6c0"}],["path",{d:"M12 21V9",key:"uvy0l4"}],["path",{d:"M19 21V3",key:"11j9sm"}]],E=p("chart-no-axes-column-increasing",k);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const b=[["path",{d:"M5 21v-6",key:"1hz6c0"}],["path",{d:"M12 21V3",key:"1lcnhd"}],["path",{d:"M19 21V9",key:"unv183"}]],j=p("chart-no-axes-column",b);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=[["path",{d:"M21 12c.552 0 1.005-.449.95-.998a10 10 0 0 0-8.953-8.951c-.55-.055-.998.398-.998.95v8a1 1 0 0 0 1 1z",key:"pzmjnu"}],["path",{d:"M21.21 15.89A10 10 0 1 1 8 2.83",key:"k2fpak"}]],L=p("chart-pie",C);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const w=[["rect",{width:"18",height:"18",x:"3",y:"3",rx:"2",key:"afitv7"}],["path",{d:"M3 9h18",key:"1pudct"}],["path",{d:"M3 15h18",key:"5xshup"}],["path",{d:"M9 3v18",key:"fh3hqa"}],["path",{d:"M15 3v18",key:"14nvp0"}]],D=p("grid-3x3",w);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v=[["path",{d:"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z",key:"1s2grr"}],["path",{d:"M20 2v4",key:"1rf3ol"}],["path",{d:"M22 4h-4",key:"gwowj6"}],["circle",{cx:"4",cy:"20",r:"2",key:"6kqj1y"}]],z=p("sparkles",v);/**
 * @license lucide-react v1.24.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M=[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["circle",{cx:"12",cy:"12",r:"6",key:"1vlfrh"}],["circle",{cx:"12",cy:"12",r:"2",key:"1c9p78"}]],R=p("target",M);function V(a,s,i){const c="\uFEFF",u=s.join(","),n=a.map(t=>s.map(o=>{const e=String(t[o]??"");return e.includes(",")||e.includes('"')||e.includes(`
`)?`"${e.replace(/"/g,'""')}"`:e}).join(",")),l=new Blob([c+u+`
`+n.join(`
`)],{type:"text/csv;charset=utf-8"}),h=URL.createObjectURL(l),r=document.createElement("a");r.href=h,r.download=i,r.click(),URL.revokeObjectURL(h)}async function $(a,s,i){const c=await y(()=>import("./xlsx.min-DAEdtGqP.js").then(t=>t.x),__vite__mapDeps([0,1,2])),u=a.map(t=>{const o={};return s.forEach(e=>{o[e]=t[e]??""}),o}),n=c.utils.json_to_sheet(u,{header:s,cellDates:!0}),l=c.utils.decode_range(n["!ref"]||"A1:A1"),h=s.map(t=>({wch:Math.max(t.length+2,12)}));for(let t=l.s.c;t<=l.e.c;++t){const o=c.utils.encode_cell({r:0,c:t});n[o]&&(n[o].s={font:{bold:!0,color:{rgb:"FF000000"}},fill:{fgColor:{rgb:"FFF3F4F6"}},border:{bottom:{style:"thin",color:{rgb:"FFCCCCCC"}}}})}for(let t=1;t<=l.e.r;++t)for(let o=l.s.c;o<=l.e.c;++o){const e=c.utils.encode_cell({r:t,c:o});if(!n[e])continue;const d=n[e].v,f=String(d);f.length>h[o].wch&&(h[o].wch=Math.min(f.length+2,50)),typeof d=="number"&&(Number.isInteger(d)?n[e].z="0":n[e].z="#,##0.00")}n["!cols"]=h;const r=c.utils.book_new();c.utils.book_append_sheet(r,n,"Donnees"),c.writeFile(r,i)}async function S(a,s,i){const c=await y(()=>import("./xlsx.min-DAEdtGqP.js").then(t=>t.x),__vite__mapDeps([0,1,2])),u=a.map(t=>{const o={};return s.forEach(e=>{const d=t[e];typeof d=="string"&&d!==""&&!isNaN(Number(d))?o[e]=Number(d):o[e]=d??""}),o}),n=c.utils.json_to_sheet(u,{header:s,cellDates:!0}),l=c.utils.decode_range(n["!ref"]||"A1:A1"),h=s.map(t=>({wch:Math.max(t.length+2,14)}));for(let t=l.s.c;t<=l.e.c;++t){const o=c.utils.encode_cell({r:0,c:t});n[o]&&(n[o].s={font:{bold:!0},fill:{fgColor:{rgb:"FF1A56DB"}},alignment:{horizontal:"center"}},h[t].wch<16&&(h[t].wch=16))}n["!cols"]=h;const r=c.utils.book_new();c.utils.book_append_sheet(r,n,"Data"),c.writeFile(r,i)}function I(a,s){var n;const i=(n=a.current)==null?void 0:n.getEchartsInstance();if(!i)return;const c=i.getDataURL({type:"png",pixelRatio:2,backgroundColor:"#fff"}),u=document.createElement("a");u.href=c,u.download=s,u.click()}function P(a){var u,n,l,h;const s=[];let i=[];if(!a||!a.series||!a.series.length)return{rows:s,cols:i};const c=a.series[0].type;if(c==="pie"){const r=a.series[0].name||"Valeur",t="Catégorie";i=[t,r],(a.series[0].data||[]).forEach(e=>{s.push({[t]:e.name,[r]:e.value})})}else if(c==="scatter"){const r=((u=a.xAxis)==null?void 0:u.name)||"X",t=((n=a.yAxis)==null?void 0:n.name)||"Y";i=[r,t],(a.series[0].data||[]).forEach(e=>{s.push({[r]:e[0],[t]:e[1]})})}else{const r=((l=a.xAxis)==null?void 0:l.name)||"X";i.push(r);const t=((h=a.xAxis)==null?void 0:h.data)||[],o=[];a.series.forEach((e,d)=>{const f=e.name||`Y${d+1}`;o.push(f),i.push(f)}),t.forEach((e,d)=>{const f={[r]:e};a.series.forEach((_,m)=>{f[o[m]]=_.data[d]}),s.push(f)})}return{rows:s,cols:i}}export{F as A,j as C,D as G,z as S,R as T,E as a,N as b,L as c,V as d,I as e,$ as f,S as g,P as h};
