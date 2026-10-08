#!/usr/bin/env node
// Immutable, forward-only EES snapshot. Reuses exactly the website scoring function.
// Do not reconstruct old "predictions" from historical replay.
const fs=require('fs'),vm=require('vm'),path=require('path');
const html=fs.readFileSync('index.html','utf8');
const configStart=html.indexOf('const stockConfig = {');
const configEnd=html.indexOf('\n};',configStart);
const fnStart=html.indexOf('function calculateEES(');
const fnEnd=html.indexOf('\nfunction showEESRadar(',fnStart);
if([configStart,configEnd,fnStart,fnEnd].some(i=>i<0))throw Error('Cannot locate exact EES scoring code');
const src=html.slice(configStart,configEnd+3)+'\n'+html.slice(fnStart,fnEnd)+'\nthis.scoreEES=calculateEES;';
const context=vm.createContext({});
new vm.Script(src,{filename:'ees-from-index.html'}).runInContext(context,{timeout:3000});
const history=JSON.parse(fs.readFileSync('history.json','utf8'));
const dates=Object.keys(history).sort();
const date=dates.at(-1);
if(!date)throw Error('No history dates');
const current=history[date];
if(!current?.stocks)throw Error('No stocks for '+date);
const outDir='ees_snapshots';fs.mkdirSync(outDir,{recursive:true});
const dest=path.join(outDir,date+'.json');
if(fs.existsSync(dest)){console.log('EES SNAPSHOT: existing immutable '+dest+'; skipped');process.exit(0);}
const scores=Object.keys(current.stocks).map(code=>context.scoreEES(code,history,date)).filter(Boolean);
scores.sort((a,b)=>b.score-a.score||a.code.localeCompare(b.code));
const payload={
 schema_version:1,model:'EES-v1-25-20-20-20-15',trade_date:date,
 generated_at:new Date().toISOString(),
 provenance:'first-run snapshot only; NOT a historical prediction; computed from history as available at capture time',
 selection_rule:'covered>=75 and score>=65 and stage is sprout or trial',
 count:scores.length,eligible_count:scores.filter(x=>x.eligible).length,
 stocks:scores
};
fs.writeFileSync(dest,JSON.stringify(payload,null,2)+'\n');
console.log('EES SNAPSHOT: created '+dest+' stocks='+scores.length+' eligible='+payload.eligible_count);
