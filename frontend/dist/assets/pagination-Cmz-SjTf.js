import{a as n}from"./index-Dgh_kphU.js";async function p(r,l=10){const a=[];let t=r,e=0;for(;t&&e<l;){const s=await n.get(t);a.push(...s.data.results??[]),t=s.data.next,e+=1}return a}export{p as f};
