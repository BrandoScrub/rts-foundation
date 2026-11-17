/* mapkit core: narrative map generation for isometric RTS games.
   Pure functions. No canvas, no DOM, no game globals. Runs under Node and inlined in a browser game.
   MapKit.generate({seed,w,h,template,context}) -> MapPlan. See mapkit/README.md.
   The map is made by simulating its history in order: land, settlement, roads, districts, history,
   approaches, population, validation. Each step reads what earlier steps wrote. */
const MapKit=(()=>{'use strict';
const TAU=Math.PI*2;
const OPEN=0,FOREST=1,ROCK=2,WATER=3,WALL=4,ORE=5;
const LAND_NAMES=['open','forest','rock','water','wall','ore'];
const DIR8=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
const SIDES={n:'north',s:'south',e:'east',w:'west'};
const OPP={n:'s',s:'n',e:'w',w:'e'};
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
function mulberry(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function hashStr(s){let h=2166136261>>>0;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0}return h}
const pick=(r,a)=>a[Math.floor(r()*a.length)];
const rint=(r,a,b)=>a+Math.floor(r()*(b-a+1));
class Heap{constructor(){this.a=[];this.k=[]}get size(){return this.a.length}
 push(v,k){const a=this.a,K=this.k;let i=a.length;a.push(v);K.push(k);while(i>0){const p=(i-1)>>1;if(K[p]<=k)break;a[i]=a[p];K[i]=K[p];i=p}a[i]=v;K[i]=k}
 pop(){const a=this.a,K=this.k,top=a[0],lv=a.pop(),lk=K.pop(),n=a.length;if(n){let i=0;for(;;){const l=2*i+1,r=l+1;let m=i,mk=lk;if(l<n&&K[l]<mk){m=l;mk=K[l]}if(r<n&&K[r]<mk){m=r;mk=K[r]}if(m===i)break;a[i]=a[m];K[i]=K[m];i=m}a[i]=lv;K[i]=lk}return top}}

/* ---------- noise ---------- */
function makeNoise(w,h,r,scale){const gw=Math.ceil(w/scale)+3,gh=Math.ceil(h/scale)+3,g=new Float32Array(gw*gh);for(let i=0;i<g.length;i++)g[i]=r();
 return(x,y)=>{const fx=x/scale,fy=y/scale,ix=Math.floor(fx),iy=Math.floor(fy),tx=fx-ix,ty=fy-iy,sx=tx*tx*(3-2*tx),sy=ty*ty*(3-2*ty),a=g[iy*gw+ix],b=g[iy*gw+ix+1],c=g[(iy+1)*gw+ix],d=g[(iy+1)*gw+ix+1];return a+(b-a)*sx+(c-a)*sy+(a-b-c+d)*sx*sy}}
function fbm3(w,h,r,s){const a=makeNoise(w,h,r,s),b=makeNoise(w,h,r,s/2.1),c=makeNoise(w,h,r,s/4.4);return(x,y)=>a(x,y)*.55+b(x,y)*.3+c(x,y)*.15}
function warpN(w,h,f,r,s,amt){const u=makeNoise(w,h,r,s),v=makeNoise(w,h,r,s);return(x,y)=>f(clamp(x+(u(x,y)-.5)*amt,0,w-1.01),clamp(y+(v(x,y)-.5)*amt,0,h-1.01))}
function cutAt(F,frac){const a=Float32Array.from(F).sort();return a[clamp(Math.floor((1-frac)*a.length),0,a.length-1)]}

/* ---------- shared search ---------- */
function makeRouter(S){const{n,w,h}=S,g=new Float64Array(n),came=new Int32Array(n),seen=new Uint32Array(n),done=new Uint32Array(n);let gen=0;
 return function route(srcs,isGoal,costAt){gen++;const heap=new Heap();for(const s of srcs){g[s]=0;seen[s]=gen;came[s]=-1;heap.push(s,0)}
  while(heap.size){const c=heap.pop();if(done[c]===gen)continue;done[c]=gen;
   if(isGoal(c)){const p=[];for(let i=c;i!==-1;i=came[i])p.push(i);return p.reverse()}
   const cx=c%w,cy=c/w|0;for(let k=0;k<8;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(nx<0||ny<0||nx>=w||ny>=h)continue;const ni=ny*w+nx;if(done[ni]===gen)continue;const st=costAt(ni);if(st===Infinity)continue;const nd=g[c]+st*(k>=4?1.414:1);if(seen[ni]!==gen||nd<g[ni]){seen[ni]=gen;g[ni]=nd;came[ni]=c;heap.push(ni,nd)}}}
  return null}}
/* Single-source field with the game's movement rule: no corner cutting past impassable tiles. */
function fieldFrom(S,srcs,stepCost,F){const{n,w,h}=S;F=F||new Float32Array(n);F.fill(1e9);const closed=new Uint8Array(n),heap=new Heap();for(const s of srcs){F[s]=0;heap.push(s,0)}
 while(heap.size){const c=heap.pop();if(closed[c])continue;closed[c]=1;const cx=c%w,cy=c/w|0;for(let k=0;k<8;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(nx<0||ny<0||nx>=w||ny>=h)continue;const ni=ny*w+nx;if(closed[ni])continue;const st=stepCost(ni);if(st===Infinity)continue;if(k>=4&&(stepCost(cy*w+nx)===Infinity||stepCost(ny*w+cx)===Infinity))continue;const nd=F[c]+st*(k>=4?1.414:1);if(nd<F[ni]){F[ni]=nd;heap.push(ni,nd)}}}
 return F}

/* ---------- state ---------- */
function makeState(o){const{seed,w,h,template:t,context:ctx}=o,n=w*h,mz=w/120,clr=ctx.clearing||10.5,S={seed:seed>>>0,w,h,n,t,ctx,mz,cz:ctx.content||mz,clr,ck:clr-10.5,sx:ctx.start.x,sy:ctx.start.y,sIdx:Math.floor(ctx.start.y)*w+Math.floor(ctx.start.x),
 land:new Uint8Array(n),ford:new Uint8Array(n),road:new Uint8Array(n),traffic:new Float32Array(n),roadId:new Int16Array(n).fill(-1),district:new Uint8Array(n),scar:new Uint8Array(n),reserved:new Uint8Array(n),cut:new Uint8Array(n),rough:new Float32Array(n),fert:new Float32Array(n),distW:new Uint8Array(n),rnoise:new Float32Array(n),tvar:new Float32Array(n),flow:new Float32Array(n),tr0:new Float32Array(n),
 occ:new Uint8Array(n),tags:[''],sites:[],roads:[],approaches:[],placements:[],chronicle:[],districts:[],coreGates:[],coreSquares:[],names:new Set(),beatDone:new Set(),fails:[],rngs:{}};
 S.rng=name=>S.rngs[name]||(S.rngs[name]=mulberry((S.seed^hashStr(name))>>>0));
 S.tag=name=>{let i=S.tags.indexOf(name);if(i<0){i=S.tags.length;S.tags.push(name)}return i};
 S.idx=(x,y)=>Math.floor(y)*w+Math.floor(x);
 S.inB=(x,y)=>x>=0&&y>=0&&x<w&&y<h;
 S.dStart=(x,y)=>Math.hypot(x+.5-S.sx,y+.5-S.sy);
 S.route=makeRouter(S);
 for(const d of (t.districts||[])){S.districts.push(d.id)}
 if(!S.districts.includes('wilds'))S.districts.push('wilds');S.distOf=id=>S.districts.indexOf(id);
 return S}

/* ---------- pass 1: land ---------- */
function passLand(S){const{w,h,n,t,ctx,land,ford,scar,tvar}=S,r=S.rng('land'),biome=ctx.biome,L=t.land||{},cov=Object.assign({},(L.coverage&&L.coverage[biome])||{water:.06,forest:.2,rock:.08}),mod=ctx.mod||{};
 for(const k of ['water','forest','rock'])if(mod[k])cov[k]=Math.max(.01,cov[k]-mod[k]*2);
 if(L.waterMin)cov.water=Math.max(cov.water,L.waterMin);if(L.forestMin)cov.forest=Math.max(cov.forest,typeof L.forestMin==='object'?(L.forestMin[biome]??.2):L.forestMin);
 if(L.rockMul)cov.rock*=L.rockMul;if(L.forestMul)cov.forest*=L.forestMul;if(L.waterMul)cov.water*=L.waterMul;
 const nw=warpN(w,h,fbm3(w,h,r,18),r,9,12),nf=warpN(w,h,fbm3(w,h,r,11),r,7,8),nb=fbm3(w,h,r,8),nrg=warpN(w,h,fbm3(w,h,r,21),r,11,14),nv=makeNoise(w,h,r,6),nc=makeNoise(w,h,r,5),nfert=fbm3(w,h,r,14),nroad=fbm3(w,h,r,6),features=L.features||[];
 const ang=r()*TAU,ca=Math.cos(ang),sa=Math.sin(ang),side=r()<.5?-1:1;S.axis={ang,ca,sa,side};
 const vOf=(x,y)=>-(x+.5-S.sx)*sa+(y+.5-S.sy)*ca,uOf=(x,y)=>(x+.5-S.sx)*ca+(y+.5-S.sy)*sa;S.vOf=vOf;S.uOf=uOf;
 const has=f=>features.find(q=>q.type===f),valley=has('valley'),rim=has('rim'),ridgeHeavy=!!L.ridgeHeavy,valOff=side*(15+r()*5),ridOff=30+r()*6,FW=new Float32Array(n),FF=new Float32Array(n),FR=new Float32Array(n),RG=new Float32Array(n);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x,d=S.dStart(x,y),rg=1-Math.abs(nrg(x,y)*2-1),ridge=rg**4;RG[i]=ridge;let wv=nw(x,y),f=nf(x,y),k=ridgeHeavy?ridge*.85+nb(x,y)*.15:ridge*.6+nb(x,y)*.4;
  if(valley){const v=vOf(x,y);k+=.5*Math.exp(-(((Math.abs(v-valOff)-ridOff)/4)**2));f+=.14*Math.exp(-(((v-valOff)/9)**2));wv-=.25}
  if(rim){f+=.18*clamp((d-26)/14,0,1);if(d<26)wv-=.3}
  FW[i]=wv;FF[i]=f;FR[i]=k;tvar[i]=r();S.rough[i]=Math.sqrt(ridge);S.fert[i]=nfert(x,y);S.rnoise[i]=nroad(x,y)}
 const tW=cutAt(FW,cov.water),tF=cutAt(FF,cov.forest),tR=cutAt(FR,cov.rock),oreF=(ctx.ore??4),tO=cutAt(RG,.01+oreF*.0012);
 for(let i=0;i<n;i++){const x=i%w,y=i/w|0,d=S.dStart(x,y);let c=OPEN;if(FW[i]>tW)c=WATER;else if(FR[i]>tR)c=ROCK;else if(FF[i]>tF)c=FOREST;if(c!==WATER&&RG[i]>tO&&d>19+S.ck&&nv(x,y)>.45)c=ORE;land[i]=c}
 const river=(far,opts)=>{opts=opts||{};const horiz=r()<.5,sd=r()<.5?-1:1,base=sd*(15+r()*10+far),p1=r()*TAU,p2=r()*TAU,p3=r()*TAU,fords=[.16+r()*.1,.44+r()*.12,.74+r()*.1].map(f=>f*w);
  for(let tt=-2;tt<w+2;tt+=.5){let lat=base+Math.sin(tt*.11+p1)*5+Math.sin(tt*.043+p2)*8;if(Math.abs(lat)<13)lat=13*Math.sign(lat||sd);const ww=1.35+Math.sin(tt*.21+p3)*.45,isFord=fords.some(f=>Math.abs(tt-f)<1.6),along=Math.floor(tt),mid=(horiz?S.sy:S.sx)+lat;
   for(let a=Math.floor(mid-ww-1);a<=mid+ww+1;a++){if(Math.abs(a+.5-mid)>ww)continue;const x=horiz?along:a,y=horiz?a:along;if(!S.inB(x,y))continue;const i=y*w+x;if(isFord){land[i]=OPEN;ford[i]=1}else if(!ford[i])land[i]=WATER}}};
 const crater=(cx,cy,rad,keepR=12+S.ck)=>{for(let y=Math.floor(cy-rad-2);y<=cy+rad+2;y++)for(let x=Math.floor(cx-rad-2);x<=cx+rad+2;x++){if(!S.inB(x,y)||S.dStart(x,y)<keepR)continue;const dd=Math.hypot(x+.5-cx,y+.5-cy),i=y*w+x;if(dd<rad*.55&&rad>1.3){land[i]=WATER;ford[i]=0;scar[i]=S.tag('churned')}else if(dd<rad+1.2){if(land[i]===FOREST)scar[i]=S.tag('burnt');else if(land[i]===OPEN)scar[i]=S.tag('churned')}}};S.crater=crater;
 for(const f of features){if(f.type==='valley'){const p1=r()*TAU,p2=r()*TAU,fs=[-.45,-.05,.38].map(q=>q*w+(r()-.5)*10);for(let u=-95*S.mz;u<95*S.mz;u+=.4){let v=valOff+Math.sin(u*.05+p1)*6+Math.sin(u*.13+p2)*2;if(Math.abs(v)<13)v=13*side;const ww=2.3+Math.sin(u*.17+p2)*.6,isF=fs.some(q=>Math.abs(u-q)<2);for(let o=-ww;o<=ww;o+=.4){const vv=v+o,x=Math.floor(S.sx+u*ca-vv*sa),y=Math.floor(S.sy+u*sa+vv*ca);if(!S.inB(x,y))continue;const i=y*w+x;if(isF){land[i]=OPEN;ford[i]=1}else if(!ford[i])land[i]=WATER}}}
  else if(f.type==='rim'){const R=22+r()*4,nr=makeNoise(w,h,r,7),gaps=[],ng=3+((r()*3)|0);for(let k=0;k<ng;k++)gaps.push(r()*TAU);S.rimR=R;for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x,dx=x+.5-S.sx,dy=y+.5-S.sy,d=Math.hypot(dx,dy),rr=R+(nr(x,y)-.5)*5,a=Math.atan2(dy,dx),inGap=gaps.some(g=>{let da=Math.abs(a-g)%TAU;if(da>Math.PI)da=TAU-da;return da*d<2.8});if(Math.abs(d-rr)<1.8){if(inGap){land[i]=OPEN;scar[i]=S.tag('churned')}else land[i]=nv(x,y)>.72?ORE:ROCK}else if(d<rr-1.8&&d>11){if(land[i]===FOREST&&nf(x,y)<tF+.06)land[i]=OPEN;if(land[i]===ROCK&&nb(x,y)<.6)land[i]=OPEN;if(Math.abs(d-rr)<4&&land[i]===OPEN&&!inGap)scar[i]=S.tag('churned')}}}
  else if(f.type==='ponds'){const m=Math.round((f.n||55)*S.mz*S.mz);for(let k=0;k<m;k++){const a=r()*TAU,dd=15+r()*45*S.mz;crater(S.sx+Math.cos(a)*dd,S.sy+Math.sin(a)*dd,1+r()*1.6)}}
  else if(f.type==='clearings'){const m=Math.round((f.n||8)*S.mz*S.mz);for(let k=0;k<m;k++){const a=r()*TAU,dd=18+r()*36*S.mz,cx=S.sx+Math.cos(a)*dd,cy=S.sy+Math.sin(a)*dd,rad=3+r()*3.5;for(let y=Math.floor(cy-rad-1);y<=cy+rad+1;y++)for(let x=Math.floor(cx-rad-1);x<=cx+rad+1;x++)if(S.inB(x,y)&&Math.hypot(x+.5-cx,y+.5-cy)<rad+(r()-.5)*1.5&&land[y*w+x]===FOREST)land[y*w+x]=OPEN}}
  else if(f.type==='river'){if(r()<(f.chance?.[biome]??f.p??1))river(f.far||0)}}
 if(S.mz>1){const m=Math.round(S.mz*S.mz*(biome==='wastes'?.7:1.2));for(let k=0;k<m;k++)river(30+r()*(w/2-48))}
 if(L.craters!==false){for(let c=0;c<Math.round(3*S.mz*S.mz);c++){const a=r()*TAU,dd=26+r()*28*S.mz,cx=S.sx+Math.cos(a)*dd,cy=S.sy+Math.sin(a)*dd;for(let k=0;k<5+((r()*4)|0);k++)crater(cx+(r()-.5)*9,cy+(r()-.5)*9,.7+r()*1.5)}}
 /* colony clearing and starting resources, as v2 guarantees. context.clearing: mean radius in tiles (default 10.5); the rings kept free
    of craters, blobs and ore, and the guaranteed open radius, move out with it */
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){const d=S.dStart(x,y);if(d<S.clr+(nc(x,y)-.5)*5){const i=y*w+x;land[i]=OPEN;ford[i]=0;scar[i]=0}}
 const blob=(cx,cy,rad,c)=>{for(let y=Math.floor(cy-rad-1);y<=cy+rad+1;y++)for(let x=Math.floor(cx-rad-1);x<=cx+rad+1;x++){if(!S.inB(x,y)||S.dStart(x,y)<9+S.ck)continue;if(Math.hypot(x+.5-cx,y+.5-cy)<rad+(r()-.5)*1.4){const i=y*w+x;land[i]=c;ford[i]=0;scar[i]=0}}};S.blob=blob;
 const ring=(a,d,rad,c)=>blob(S.sx+Math.cos(a)*d,S.sy+Math.sin(a)*d,rad,c);S.ring=ring;
 const a1=r()*TAU;ring(a1,13,4.2,FOREST);ring(a1+Math.PI*(.8+r()*.4),16,3.2,FOREST);const a2=a1+Math.PI*(.5+r()*.4);ring(a2,13.5,3,ROCK);const a3=a2+Math.PI*(.45+r()*.4);ring(a3,15,2.6,WATER);const a4=a1-Math.PI*(.35+r()*.4);ring(a4,18,2.1,ORE);
 for(let k=0;k<Math.round((oreF+2)*S.mz*S.mz);k++)ring(r()*TAU,22+r()*30*S.mz,1.5+r()*1.1,ORE);
 for(let k=0;k<3;k++)ring(r()*TAU,23+r()*14,2.4+r()*2,FOREST);ring(r()*TAU,24+r()*16,2+r()*1.4,ROCK);if(S.mz>1){const m=Math.round(10*S.mz*S.mz);for(let k=0;k<m;k++)ring(r()*TAU,42+r()*(w/2-50),2.4+r()*3,r()<.65?FOREST:ROCK)}
 refreshFields(S)}
function refreshFields(S){const{w,h,n,land,distW}=S;distW.fill(255);const q=[];for(let i=0;i<n;i++)if(land[i]===WATER){distW[i]=0;q.push(i)}for(let qi=0;qi<q.length;qi++){const c=q[qi],cx=c%w,cy=c/w|0,dc=distW[c];if(dc>=60)continue;for(let k=0;k<4;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx;if(distW[ni]>dc+1){distW[ni]=dc+1;q.push(ni)}}}}

/* ---------- pass 2: settlement ---------- */
function roadBase(S,i){return (S.t.roadCost||[1,5,14,60,200,14])[S.land[i]]}
function pass2Settlement(S){const{w,h,t,land}=S,r=S.rng('settlement');
 fieldFrom(S,[S.sIdx],i=>{const l=land[i];return l===WATER?20:l===ROCK||l===ORE?8:l===FOREST?2.5:1},S.tr0);
 S.sites.push({id:'s0',kind:t.startKind||'start',name:t.startName||'the Colony',x:Math.floor(S.sx),y:Math.floor(S.sy),radius:10,importance:5,era:'present',state:'held',tags:['start']});
 const mkName=kind=>makeName(S,r,kind);
 const sL=t.sites||[];for(const spec of sL){const cnt=Array.isArray(spec.count)?rint(r,Math.round(spec.count[0]*S.mz),Math.round(spec.count[1]*S.mz*S.mz)):Math.round(spec.count*(spec.fixed?1:S.mz*S.mz)),want=spec.want||{},cands=[];
  const near=(l,x,y,rad)=>{for(let yy=y-rad;yy<=y+rad;yy+=Math.max(1,rad>>1))for(let xx=x-rad;xx<=x+rad;xx+=Math.max(1,rad>>1))if(S.inB(xx,yy)&&land[yy*w+xx]===l)return true;return false};
  for(let y=4;y<h-4;y+=3)for(let x=4;x<w-4;x+=3){const i=y*w+x,lc=land[i];if(lc===WATER||(lc!==OPEN&&!spec.anyLand))continue;
   const margin=spec.seat?(spec.radius||11)*Math.pow(S.mz,.6)+4:Math.max(4,spec.margin||4);if(x<margin||y<margin||x>=w-margin||y>=h-margin)continue;
   let sc=r()*.4;
   if(want.travel){const[a,b]=want.travel,sc2=S.mz,d=S.tr0[i];if(d>=1e9||d<a*sc2||d>b*sc2)continue;sc+=want.travelW||0}
   else if(S.tr0[i]>=1e9)continue;
   if(want.minStart&&S.dStart(x,y)<want.minStart*(want.scale?S.mz:1))continue;
   if(want.flat)sc+=want.flat*(1-S.rough[i]);if(want.water&&S.distW[i]<want.water[0])sc+=want.water[1]*(1-S.distW[i]/want.water[0]);if(want.waterHard&&S.distW[i]>want.waterHard)continue;
   if(want.fertile)sc+=want.fertile*S.fert[i];if(want.high)sc+=want.high*S.rough[i];
   if(want.rock){if(!near(ROCK,x,y,want.rock[0]))continue;sc+=want.rock[1]}if(want.ore){if(!near(ORE,x,y,want.ore[0]))continue;sc+=want.ore[1]}if(want.forest){if(!near(FOREST,x,y,want.forest[0]))continue;sc+=want.forest[1]}
   let ok=true;if(want.nearKind){const[kd,a,b,wgt]=want.nearKind;let best=1e9;for(const s of S.sites)if(s.kind===kd){const dd=Math.hypot(s.x-x,s.y-y);if(dd<best)best=dd}if(best>=1e9){if(want.nearRequired)ok=false}else if(best<a||best>b)ok=false;else sc+=wgt*(1-(best-a)/(b-a+1))}
   if(!ok)continue;cands.push({x,y,sc})}
  cands.sort((a,b)=>b.sc-a.sc||a.y-b.y||a.x-b.x);let made=0;
  for(const c of cands){if(made>=cnt)break;let clash=false;for(const s of S.sites){const need=s.kind===spec.kind?(spec.spacing||14):8;if(Math.hypot(s.x-c.x,s.y-c.y)<need+(s.seat?s.radius+4:0)){clash=true;break}}if(clash)continue;
   const s={id:'s'+S.sites.length,kind:spec.kind,name:mkName(spec.kind),x:c.x,y:c.y,radius:Math.round((spec.radius||3)*(spec.seat?Math.pow(S.mz,.6):1)),importance:spec.importance||2,era:spec.era||'settled',state:'intact',tags:spec.tags?spec.tags.slice():[]};if(spec.seat){s.seat=true;S.seat=s}S.sites.push(s);made++}
  if(spec.seat&&!S.seat){const c=cands.length?cands[0]:{x:Math.floor(S.sx+(r()<.5?-1:1)*30*S.mz),y:Math.floor(S.sy)};const s={id:'s'+S.sites.length,kind:spec.kind,name:mkName(spec.kind),x:c.x,y:c.y,radius:Math.round((spec.radius||11)*Math.pow(S.mz,.6)),importance:spec.importance||8,era:'settled',state:'intact',tags:[],seat:true};S.seat=s;S.sites.push(s)}}
 S.sites.sort((a,b)=>(b.seat?1:0)-(a.seat?1:0)||(b.importance-a.importance)||0)}
function makeName(S,r,kind){const N=S.t.names||{},tries=20;const pool=N[kind]||N.default;for(let k=0;k<tries;k++){let nm;if(!pool)nm='Site '+S.names.size;else{const pat=pool[Math.floor(r()*pool.length)];nm=pat.replace(/\{P\}/g,()=>pick(r,N.prefix||['Ash'])+pick(r,N.suffix||['by'])).replace(/\{S\}/g,()=>pick(r,N.saint||['Bell']))}if(!S.names.has(nm)){S.names.add(nm);return nm}}const f=(pool?'':'')+S.t.names?.default?.[0]?.replace(/\{P\}.*/,'')+'X'+S.names.size;S.names.add(f);return f}

/* ---------- pass 3: roads ---------- */
function layPath(S,path,weight,eid){const{w,traffic,road,roadId,land,ford}=S;let prev=-1;const added=[];const add=i=>{traffic[i]+=weight;road[i]=road[i]||1;if(roadId[i]<0)roadId[i]=eid;added.push(i)};
 for(const i of path){if(prev>=0){const px=prev%w,py=prev/w|0,x=i%w,y=i/w|0;if(px!==x&&py!==y){const a=y*w+px,b=py*w+x;add(land[a]===WATER?b:a)}}add(i);prev=i}return added}
function stampRoads(S,tiles){const{w,h,traffic,road,land,ford}=S;const list=tiles||null,N=list?list.length:S.n;
 const cls=t=>t>=5?3:t>=3?2:1;
 for(let k=0;k<N;k++){const i=list?list[k]:k;if(!traffic[i])continue;const c=cls(traffic[i]);const x=i%w,y=i/w|0,br=c>=3?1:0,br2=c>=2?1:br;
  for(let dy=-br;dy<=(c>=2?1:br);dy++)for(let dx=-br;dx<=br2;dx++){const nx=x+dx,ny=y+dy;if(!S.inB(nx,ny))continue;const j=ny*w+nx;if(land[j]===ROCK||land[j]===ORE||land[j]===WALL)S.cut[j]=1;if(land[j]===WATER){land[j]=OPEN;ford[j]=1}else if(land[j]!==OPEN){land[j]=OPEN}if(road[j]<c)road[j]=c;if(S.roadId[j]<0)S.roadId[j]=S.roadId[i];if(traffic[j]===0)traffic[j]=traffic[i]*.001}}}
function addBridge(S,path,base){const{w,land}=S;let run=[];const flush=()=>{if(run.length>=2||(run.length&&S.t.bridgeAll)){const m=run[run.length>>1],name=`${base} Bridge`;S.sites.push({id:'s'+S.sites.length,kind:S.t.bridgeKind||'bridge',name:uniq(S,name),x:m%w,y:m/w|0,radius:2,importance:3,era:'settled',state:'intact',tags:['crossing'],tiles:run.slice()})}run=[]};for(const i of path){if(land[i]===WATER)run.push(i);else flush()}flush()}
function uniq(S,nm){let f=nm,k=2;while(S.names.has(f)){f=nm+' '+['','','II','III','IV'][k]||nm+k;k++}S.names.add(f);return f}
function addEdge(S,o){const e=Object.assign({id:'r'+S.roads.length,class:1,state:'open',traffic:0},o);e.idx=S.roads.length;S.roads.push(e);return e}
function nodeName(S,id){if(id.startsWith('edge:'))return sideLabel(S,id.slice(5));const s=S.sites.find(q=>q.id===id);return s?s.name:'?'}
function sideLabel(S,side){const e=S.ctx.edges&&S.ctx.edges[side];return e&&e.name?e.name:SIDES[side]}
function rimTiles(S,side){const{w,h}=S,a=[];if(side==='n')for(let x=0;x<w;x++)a.push(x);else if(side==='s')for(let x=0;x<w;x++)a.push((h-1)*w+x);else if(side==='w')for(let y=0;y<h;y++)a.push(y*w);else for(let y=0;y<h;y++)a.push(y*w+w-1);return a}
function pass3Roads(S){const{w,h,n,t,ctx,land,road,traffic}=S,r=S.rng('roads');
 const cost=(far)=>i=>{let c=roadBase(S,i)*(1+S.rnoise[i]*.6);if(road[i]&&(!far||S.dStart(i%w,i/w|0)>far))c*=.33;return c};
 const openSides=Object.keys(SIDES).filter(k=>!ctx.edges||ctx.edges[k]?.open!==false);S.openSides=openSides;
 const seat=S.seat,seatI=S.idx(seat.x,seat.y),startI=S.sIdx;
 const rim=side=>{const set=new Set(rimTiles(S,side));return i=>set.has(i)};
 // highway: two exits through the seat, toward real neighbours, infected first
 const score=k=>{const e=ctx.edges&&ctx.edges[k];return e?(e.neighbor?2:0)+(e.infected?1:0):0};const ranked=openSides.slice().sort((a,b)=>score(b)-score(a)||(r()-.5));
 const hA=ranked[0],hB=openSides.includes(OPP[hA])?OPP[hA]:(ranked[1]||hA);S.hwySides=[hA,hB];
 const seatTiles=[seatI];const place=(srcs,goal,c,weight,fromId,toId,base)=>{const p=S.route(srcs,goal,c);if(!p)return null;addBridge(S,p,base);const e=addEdge(S,{from:fromId,to:toId,path:p,base});layPath(S,p,weight,e.idx);return e};
 place(seatTiles,rim(hA),cost(0),6,seat.id,'edge:'+hA,seat.name);if(hB!==hA)place(seatTiles,rim(hB),cost(0),6,seat.id,'edge:'+hB,seat.name);
 // the road from the player start to the seat
 const sSite=S.sites.find(s=>s.tags.includes('start'));place([startI],i=>i===seatI||road[i]>0,cost(14),3,sSite.id,seat.id,seat.name);
 // every other site in importance order, to the nearest road
 for(const s of S.sites){if(s===seat||s===sSite||s.tags.includes('crossing'))continue;const si=S.idx(s.x,s.y);if(road[si])continue;const p=S.route([si],i=>road[i]>0&&i!==si,cost(0));if(!p)continue;const goal=p[p.length-1],je=S.roads[S.roadId[goal]];let toId=seat.id;if(je){const dd=id=>{if(id.startsWith('edge:'))return 1e9;const q=S.sites.find(x=>x.id===id);return q?Math.hypot(q.x-goal%w,q.y-(goal/w|0)):1e9};toId=dd(je.from)<=dd(je.to)?je.from:je.to}addBridge(S,p,s.name);const e=addEdge(S,{from:s.id,to:toId,path:p,base:s.name,lane:true});layPath(S,p,1,e.idx)}
 // bridges found while laying are sites too: give each its road (already on one), and start links to every open side
 for(const k of openSides){if(k===hA||k===hB)continue;place([startI],rim(k),cost(18),2,sSite.id,'edge:'+k,sideLabel(S,k))}
 stampRoads(S);
 for(const k of openSides){for(const i of rimTiles(S,k)){if(!road[i])continue;const x=i%w,y=i/w|0;for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){if(!S.inB(x+dx,y+dy))continue;const j=(y+dy)*w+x+dx;if(land[j]!==OPEN){if(land[j]===WATER){land[j]=OPEN;S.ford[j]=1}else land[j]=OPEN}}}}
 for(const e of S.roads){const trs=e.path.map(i=>traffic[i]).sort((a,b)=>a-b),med=trs[trs.length>>1];let tot=0;for(const q of trs)tot+=q;e.traffic=Math.round(tot/e.path.length*10)/10;e.class=med>=5?3:med>=3?2:1;const nm=e.to.startsWith('edge:')&&!S.hwySides.includes(e.to.slice(5))?((S.t.roadNames||{}).edge||'the {a} road'):((S.t.roadNames||{})[e.class]||'the {a} road'),other=[e.from,e.to].map(id=>nodeName(S,id)).find(q=>q!==e.base)||e.base;e.name=e.lane?(S.t.roadNames&&S.t.roadNames[1]||'{a} Lane').replace('{a}',e.base):nm.replace('{a}',e.base);e.other=other;delete e.base}
 uniqueRoadNames(S)}
function uniqueRoadNames(S){const seen=new Map();for(const e of S.roads){const k=e.name;if(seen.has(k)&&e.other){e.name=`${k} to ${e.other}`}seen.set(e.name,1)}}

/* ---------- pass 4: districts ---------- */
function pass4Districts(S){const{n,w,h,t,land,road,district}=S,wilds=S.distOf('wilds'),byK=t.districtOf||{};district.fill(wilds);const key=new Float32Array(n).fill(1e9),heap=new Heap(),owner=new Int16Array(n).fill(-1),sites=S.sites;
 sites.forEach((s,si)=>{const d=byK[s.kind]||byK.default;if(!d)return;const i=S.idx(s.x,s.y);key[i]=0;owner[i]=si;heap.push(i,0)});
 while(heap.size){const c=heap.pop(),cx=c%w,cy=c/w|0,k=key[c],s=sites[owner[c]],d=byK[s.kind]||byK.default,reach=d[1]*Math.sqrt(S.mz)*(s.seat?Math.pow(S.mz,.2):1)*(s.reachMul||1);if(k>reach)continue;const idx=S.distOf(d[0]);if(idx>=0)district[c]=idx;
  for(let q=0;q<4;q++){const nx=cx+DIR8[q][0],ny=cy+DIR8[q][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx,l=land[ni];const st=road[ni]?.5:(l===OPEN?1:l===FOREST?1.8:l===WATER?9:5);const nk=k+st;if(nk<key[ni]){key[ni]=nk;owner[ni]=owner[c];heap.push(ni,nk)}}}}

/* ---------- pass 5: history ---------- */
const WHERE={
 seat:S=>S.seat?{site:S.seat,x:S.seat.x,y:S.seat.y}:null,
 start:S=>({site:S.sites.find(s=>s.tags.includes('start')),x:Math.floor(S.sx),y:Math.floor(S.sy)}),
 site:(S,b,r,w)=>{const L=S.sites.filter(s=>s.kind===w.kind&&s.state!=='gone'&&(!w.tag||s.tags.includes(w.tag)));return L.length?{site:pick(r,L),x:0,y:0,_set:1}:null},
 bridge:(S,b,r,w)=>{const L=S.sites.filter(s=>s.tags.includes('crossing')&&s.state==='intact');return L.length?{site:pick(r,L),_set:1}:null},
 roadSpot:(S,b,r,w)=>{const L=S.roads.filter(e=>e.class>=(w.minClass||2)&&e.state==='open'&&e.path.length>20);if(!L.length)return null;const e=pick(r,L),i=e.path[(e.path.length*(.3+r()*.4))|0];return{road:e,x:i%S.w,y:i/S.w|0,site:siteNear(S,i%S.w,i/S.w|0)}},
 wilds:(S,b,r,w)=>{const wd=S.distOf('wilds'),far=w.far||14;for(let g=0;g<600;g++){const x=rint(r,6,S.w-7),y=rint(r,6,S.h-7),i=y*S.w+x;if(S.district[i]!==wd||S.land[i]!==OPEN||S.dStart(x,y)<30*S.mz*.8)continue;if(!awayFromRoad(S,x,y,far))continue;return{x,y,site:siteNear(S,x,y)}}return null},
 farmland:(S,b,r,w)=>{const d=S.distOf(w.district||'farmland');for(let g=0;g<400;g++){const x=rint(r,4,S.w-5),y=rint(r,4,S.h-5),i=y*S.w+x;if(S.district[i]!==d||S.dStart(x,y)<(w.min||26)*S.mz)continue;if(S.land[i]===OPEN)return{x,y,site:siteNear(S,x,y)}}return null},
 riverLow:(S,b,r,w)=>{let best=null,bs=-1;for(let g=0;g<300;g++){const x=rint(r,6,S.w-7),y=rint(r,6,S.h-7),i=y*S.w+x;if(S.land[i]!==OPEN||S.distW[i]>4||S.dStart(x,y)<24)continue;const sc=(S.seat?Math.max(0,40-Math.hypot(x-S.seat.x,y-S.seat.y)):1)+r()*5;if(sc>bs){bs=sc;best={x,y,site:siteNear(S,x,y)}}}return best},
 evac:(S,b,r,w)=>{const L=S.roads.filter(e=>e.class===3&&e.path.length>16);if(!L.length)return null;const threat=S.ctx.threatSide,safe=L.slice().sort((a,c)=>(a.to==='edge:'+threat?1:0)-(c.to==='edge:'+threat?1:0));const e=safe[0],bi=e.path.findIndex(i=>S.ford[i]);return{road:e,site:S.seat,side:e.to.startsWith('edge:')?e.to.slice(5):'n',path:e.path,x:e.path[e.path.length>>1]%S.w,y:e.path[e.path.length>>1]/S.w|0,bridgeAt:bi}},
 choke:(S,b,r,w)=>{const L=[];for(const a of S.approaches)for(const c of a.chokepoints)if(c.d>(w.min||12)&&!S.beatDone.has('ck'+c.x+','+c.y)&&(!w.kind||c.kind===w.kind))L.push({a,c});if(!L.length)return null;const q=pick(r,L);S.beatDone.add('ck'+q.c.x+','+q.c.y);return{x:q.c.x,y:q.c.y,site:siteNear(S,q.c.x,q.c.y),approach:q.a,choke:q.c,road:q.a.roadIds[0]!=null?S.roads[q.a.roadIds[0]]:null}},
 lastStand:(S,b,r,w)=>{const a=S.approaches.slice().filter(q=>!q.fromSite).sort((p,q)=>q.weight-p.weight)[0];if(!a)return null;let best=null,bs=-1e9;const seat=S.seat,P=a.path;for(let k=Math.floor(P.length*.25);k<P.length*.75;k++){const i=P[k],x=i%S.w,y=i/S.w|0,ds=S.dStart(x,y);if(ds<20)continue;const toLine=seat?distToSeg(x,y,S.sx,S.sy,seat.x,seat.y):0,sc=(S.road[i]>=2?3:0)-toLine*.05-Math.abs(ds-30*S.mz)*.04+r()*.5;if(sc>bs){bs=sc;best={x,y,approach:a,site:siteNear(S,x,y),road:a.roadIds[0]!=null?S.roads[a.roadIds[0]]:null}}}return best},
 behindFront:(S,b,r,w)=>{const L=S.roads.filter(e=>e.state==='open'&&e.path.length>14);if(!L.length)return null;for(let g=0;g<60;g++){const e=pick(r,L),i=e.path[(e.path.length*(.2+r()*.6))|0],x=i%S.w,y=i/S.w|0;if(S.dStart(x,y)<22*S.mz||S.land[i]!==OPEN||S.reserved[i]||isCore(S,x,y))continue;return{road:e,x,y,site:siteNear(S,x,y)}}return null},
 seatSide:(S,b,r,w)=>S.seat?{site:S.seat,x:S.seat.x,y:S.seat.y,face:pick(r,['n','s','e','w'])}:null,
 axisFront:(S,b,r,w)=>({x:Math.floor(S.sx),y:Math.floor(S.sy),site:S.seat}),
};
function siteNear(S,x,y){let b=null,bd=1e9;for(const s of S.sites){if(s.tags.includes('crossing')||s.tags.includes('start'))continue;const d=(s.x-x)**2+(s.y-y)**2;if(d<bd){bd=d;b=s}}return b||S.sites[0]}
function awayFromRoad(S,x,y,rad){for(let yy=y-rad;yy<=y+rad;yy+=2)for(let xx=x-rad;xx<=x+rad;xx+=2)if(S.inB(xx,yy)&&S.road[yy*S.w+xx])return false;return true}
function distToSeg(px,py,ax,ay,bx,by){const dx=bx-ax,dy=by-ay,t=clamp(((px-ax)*dx+(py-ay)*dy)/((dx*dx+dy*dy)||1),0,1);return Math.hypot(px-ax-t*dx,py-ay-t*dy)}
function keepClear(S,x,y){return S.dStart(x,y)<13+S.ck}
function setWall(S,i,tag){S.land[i]=WALL;S.ford[i]=0;if(tag)S.scar[i]=S.tag(tag)}
function isRoadish(S,i){return S.road[i]>0||S.ford[i]>0}
const OPS={
 /* the seat: streets on a grid, blocks of ruins, a wall with gaps */
 core(C,op){const{S,loc}=C,{w,h,land,ford,road,scar,district}=S,seat=loc.site,R=seat.radius,cx=seat.x,cy=seat.y,x0=cx-R,x1=cx+R,y0=cy-R,y1=cy+R,core=S.distOf('core'),r=C.r,pitch=op.pitch||6,dens=op.density??.72;S.coreRect={x0,y0,x1,y1};
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){if(!S.inB(x,y))continue;const i=y*w+x;land[i]=OPEN;ford[i]=0;scar[i]=0;if(core>=0)district[i]=core}
  const ring=(x,y)=>x<=x0+1||x>=x1-1||y<=y0+1||y>=y1-1,inner=(x,y)=>x>x0+1&&x<x1-1&&y>y0+1&&y<y1-1,squares=[];
  // find where roads reach the wall line (sides only, away from corners)
  const gatesAll=[];const scan=(side,fix,fix2,alongA,alongB,vert)=>{let cur=[];const flush=()=>{if(cur.length){let t=0,m=0;for(const q of cur){t+=q.tr;}m=cur[cur.length>>1].a;gatesAll.push({side,pos:clamp(m,alongA+3,alongB-3),tr:t});cur=[]}};for(let a=alongA;a<=alongB;a++){const x=vert?fix:a,y=vert?a:fix,i=S.inB(x,y)?y*w+x:-1;if(i>=0&&road[i]){cur.push({a,tr:S.traffic[i]})}else flush()}flush()};
  scan('n',y0,y0-1,x0,x1,false);scan('s',y1,y1+1,x0,x1,false);scan('w',x0,x0-1,y0,y1,true);scan('e',x1,x1+1,y0,y1,true);
  gatesAll.sort((a,b)=>b.tr-a.tr);const gates=[];for(const g of gatesAll){if(gates.length>=4)break;if(gates.some(q=>q.side===g.side&&Math.abs(q.pos-g.pos)<7))continue;gates.push(g)}
  const faces=['n','s','e','w'];while(gates.length<2){const sd=faces.find(f=>!gates.some(g=>g.side===f))||'n',alo=(sd==='n'||sd==='s')?cx:cy;gates.push({side:sd,pos:alo+(gates.length?5:0),tr:0})}
  // ring wall
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){if(!S.inB(x,y))continue;if(ring(x,y)){const i=y*w+x;setWall(S,i,'rampart');road[i]=0}}
  // blocks and streets
  for(let y=y0+2;y<y1-1;y++)for(let x=x0+2;x<x1-1;x++){const i=y*w+x,dx=x-x0,dy=y-y0,street=((dx%pitch)<2)||((dy%pitch)<2);if(street){if(!road[i])road[i]=1;continue}if(r()<dens){setWall(S,i,'ruin')}}
  // squares (block centres for hamlets and caches)
  for(let by=pitch;by<2*R-pitch+2;by+=pitch)for(let bx=pitch;bx<2*R-pitch+2;bx+=pitch){if(r()<.5)continue;const sx=x0+bx+2,sy=y0+by+2,sq=[];for(let q=0;q<4;q++)for(let p=0;p<4;p++){const i=(sy+q)*w+sx+p;land[i]=OPEN;scar[i]=S.tag('churned');sq.push(i)}squares.push({x:sx,y:sy})}
  S.coreSquares=squares;
  // gates: open the wall 3 wide and reserve a 3x3 plug; the plug is the blocker
  S.coreGates=[];for(const g of gates){const horiz=g.side==='n'||g.side==='s';let gx,gy;if(g.side==='n'){gx=g.pos-1;gy=y0}else if(g.side==='s'){gx=g.pos-1;gy=y1-2}else if(g.side==='w'){gx=x0;gy=g.pos-1}else{gx=x1-2;gy=g.pos-1}
   for(let dy=0;dy<3;dy++)for(let dx=0;dx<3;dx++){const x=gx+dx,y=gy+dy;if(!S.inB(x,y))continue;const i=y*w+x;land[i]=OPEN;ford[i]=0;S.reserved[i]=1;scar[i]=0}
   // street in from the gate
   for(let k=1;k<=pitch+1;k++){const lx=g.side==='w'?gx+2+k:g.side==='e'?gx-k:0,ly=g.side==='n'?gy+2+k:g.side==='s'?gy-k:0;for(let o=0;o<3;o++){const x=horiz?gx+o:lx,y=horiz?ly:gy+o;if(!S.inB(x,y))continue;const i=y*w+x;if(ring(x,y))continue;land[i]=OPEN;if(!road[i])road[i]=1}}
   const ox=g.side==='w'?gx-1:g.side==='e'?gx+3:gx+1,oy=g.side==='n'?gy-1:g.side==='s'?gy+3:gy+1;S.coreGates.push({x:gx,y:gy,side:g.side,ox,oy})}
  // seal check: anything inside not reached from a gate returns to ruin
  const seen=new Uint8Array(S.n),q=[];for(const g of S.coreGates){for(let dy=0;dy<3;dy++)for(let dx=0;dx<3;dx++){const i=(g.y+dy)*w+g.x+dx;if(!seen[i]){seen[i]=1;q.push(i)}}}
  while(q.length){const c=q.pop(),px=c%w,py=c/w|0;for(let k=0;k<4;k++){const nx=px+DIR8[k][0],ny=py+DIR8[k][1];if(nx<x0||nx>x1||ny<y0||ny>y1||!S.inB(nx,ny))continue;const ni=ny*w+nx;if(seen[ni]||land[ni]!==OPEN)continue;seen[ni]=1;q.push(ni)}}
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){if(!S.inB(x,y))continue;const i=y*w+x;if(land[i]===OPEN&&!seen[i])setWall(S,i,'ruin')}
  // block centres that are mostly ruin: the adapter draws a dead building on each
  for(let by=y0+2;by<y1-1;by+=pitch)for(let bx=x0+2;bx<x1-1;bx+=pitch){let c=0;for(let q=0;q<4;q++)for(let p=0;p<4;p++){const i=(by+q)*w+bx+p;if(S.inB(bx+p,by+q)&&land[i]===WALL)c++}if(c>=7)addP(S,C,{type:'prop',kind:'ruin-block',x:bx+1,y:by+1,siteId:seat.id})}
  // ring road between gates outside the wall, and a named site for each gate
  const out=(i)=>{const x=i%w,y=i/w|0;return x>=x0-1&&x<=x1+1&&y>=y0-1&&y<=y1+1};const gateSites=S.coreGates.map(g=>{const nm=uniq(S,`${seat.name} ${SIDES[g.side][0].toUpperCase()+SIDES[g.side].slice(1)} Gate`),s={id:'s'+S.sites.length,kind:S.t.gateKind||'gate',name:nm,x:g.x+1,y:g.y+1,radius:2,importance:6,era:'settled',state:'held',tags:['gate']};S.sites.push(s);g.siteId=s.id;return s});
  const inRect=i=>{const x=i%w,y=i/w|0;return x>=x0&&x<=x1&&y>=y0&&y<=y1},c2=i=>{if(inRect(i))return Infinity;let c=roadBase(S,i)*(1+S.rnoise[i]*.4);if(road[i])c*=.33;return c};
  const order=S.coreGates.map((g,k)=>({g,k,a:Math.atan2(g.oy+.5-cy,g.ox+.5-cx)})).sort((a,b)=>a.a-b.a);
  for(let k=0;k<order.length;k++){const a=order[k],b=order[(k+1)%order.length];if(order.length===2&&k===1)continue;const ai=S.idx(clamp(a.g.ox,0,w-1),clamp(a.g.oy,0,h-1)),bi=S.idx(clamp(b.g.ox,0,w-1),clamp(b.g.oy,0,h-1));const p=S.route([ai],i=>i===bi,i=>{if(inRect(i))return Infinity;return c2(i)});if(!p)continue;addBridge(S,p,seat.name+' Ring');const e=addEdge(S,{from:gateSites[a.k].id,to:gateSites[b.k].id,path:p,name:`the ${seat.name} Ring`,class:2,ring:true});const added=layPath(S,p,3,e.idx);stampRoads(S,added)}},
 trench(C,op){const{S,r}=C,{w,h}=S,{ca,sa,side}=S.axis,lines=op.lines||[[18,22],[14,18]];const offs=[];let base=side*(lines[0][0]+r()*(lines[0][1]-lines[0][0]));offs.push(base);for(let k=1;k<lines.length;k++){base=base+side*(lines[k][0]+r()*(lines[k][1]-lines[k][0]));offs.push(base)}S.frontOffs=offs;
  const tagT=S.tag('trench');offs.forEach((off,li)=>{const p=r()*TAU,gp=r()*13;for(let u=-95*S.mz;u<95*S.mz;u+=.25){const zz=((u/5)%2+2)%2,zig=(zz<1?zz:2-zz)*2.6-1.3,v=off+Math.sin(u*.06+p)*3.5+zig,gap=((u+gp)%13+13)%13<2.8||(li===1&&Math.sin(u*.09+p)>.45);for(const vv of [v-.45,v+.45]){const x=Math.floor(S.sx+u*ca-vv*sa),y=Math.floor(S.sy+u*sa+vv*ca);if(!S.inB(x,y)||keepClear(S,x,y))continue;const i=y*w+x;if(isRoadish(S,i)||S.scar[i]===S.tag('trench'))continue;if(S.coreRect&&x>=S.coreRect.x0&&x<=S.coreRect.x1&&y>=S.coreRect.y0&&y<=S.coreRect.y1)continue;if(gap){if(S.land[i]===WALL){}else{S.land[i]=OPEN;S.scar[i]=S.tag('churned')}}else{setWall(S,i,'trench');}}}});
  const lo=Math.min(...offs)+2,hi=Math.max(...offs)-2,fr=S.distOf('front');
  for(let i=0;i<S.n;i++){const x=i%w,y=i/w|0,v=S.vOf(x,y);if(v>lo-1&&v<hi+1){if(S.land[i]===FOREST)S.scar[i]=S.tag('burnt');if(fr>=0&&S.land[i]===OPEN&&!isCore(S,x,y))S.district[i]=fr}}
  S.frontLo=lo;S.frontHi=hi;if(op.craters){const m=Math.round(op.craters*S.mz);for(let k=0;k<m;k++){const u=(r()-.5)*170*S.mz,v=lo+r()*(hi-lo),x=S.sx+u*ca-v*sa,y=S.sy+u*sa+v*ca;if(!S.inB(Math.floor(x),Math.floor(y))||isRoadish(S,S.idx(x,y)))continue;S.crater(x,y,.8+r()*1.9)}}},
 craters(C,op){const{S,loc,r}=C,n=Math.round((op.n||10)*S.mz),rad=op.r||6;for(let k=0;k<n;k++){const x=loc.x+(r()-.5)*2*rad,y=loc.y+(r()-.5)*2*rad;if(!S.inB(Math.floor(x),Math.floor(y))||isRoadish(S,S.idx(x,y)))continue;S.crater(x,y,.7+r()*1.4)}},
 wreckLine(C,op){const{S,loc,r}=C,path=loc.path||(loc.road&&loc.road.path);if(!path)return;const tagW=S.tag(op.tag||'wreck'),n=rint(r,...(op.n||[6,12]));let made=0,start=clamp((loc.bridgeAt>=0?loc.bridgeAt:path.length*.4)|0,0,path.length-1),k=start;for(let tries=0;tries<400&&made<n;tries++){k=clamp(k+rint(r,1,3),0,path.length-1);if(k>=path.length-2)k=start=rint(r,4,path.length-5);const i=path[k],x=i%S.w,y=i/S.w|0;for(let o of [2,-2,3,-3]){const nb=path[clamp(k+1,0,path.length-1)],dx=(nb%S.w)-x,dy=(nb/S.w|0)-y,len=Math.hypot(dx,dy)||1,px=Math.round(x-dy/len*o),py=Math.round(y+dx/len*o);if(!S.inB(px,py))continue;const j=py*S.w+px;if(S.land[j]!==OPEN||S.road[j]||S.ford[j]||keepClear(S,px,py)||S.occ[j])continue;S.land[j]=ORE;S.scar[j]=tagW;S.occ[j]=1;addP(S,C,{type:'prop',kind:'wreck',x:px,y:py,siteId:loc.site?loc.site.id:null});made++;break}}},
 cutBridge(C,op){const{S,loc,r}=C,br=loc.site;if(!br||!br.tiles)return;const{land,ford,road}=S,w=S.w;for(const i of br.tiles){const x=i%w,y=i/w|0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const j=(y+dy)*w+x+dx;if(j>=0&&j<S.n&&ford[j]){land[j]=WATER;ford[j]=0;road[j]=0;S.traffic[j]=0}}}br.state='cut';for(const e of S.roads)if(e.path.some(i=>br.tiles.includes(i))&&e.state!=='faded')e.state='cut';
  // the ford: narrowest water near the bridge, route bank to bank with the bridge forbidden
  const m=br.tiles[br.tiles.length>>1],mx=m%w,my=m/w|0;let bankA=-1,bankB=-1;for(let rad=3;rad<16&&(bankA<0||bankB<0);rad++){for(let a=0;a<16;a++){const x=Math.round(mx+Math.cos(a/16*TAU)*rad),y=Math.round(my+Math.sin(a/16*TAU)*rad);if(!S.inB(x,y))continue;const j=y*w+x;if(land[j]===OPEN){if(bankA<0)bankA=j;else if(bankB<0&&Math.hypot(x-(bankA%w),y-(bankA/w|0))>4+br.tiles.length)bankB=j}}}
  if(bankA>=0&&bankB>=0){const p=S.route([bankA],i=>i===bankB,i=>{if(br.tiles.includes(i))return Infinity;return land[i]===WATER?6:land[i]===OPEN?1:40});if(p){const e=addEdge(S,{from:br.id,to:br.id,path:p,name:`${br.name} ford`,class:1,ford:true});const add=layPath(S,p,.8,e.idx);stampRoads(S,add);for(const i of p){if(land[i]===WATER){land[i]=OPEN;ford[i]=1}}}}
  const bx=mx,by=my,home=S.dStart(bx-3,by)<S.dStart(bx+3,by)?-1:1;for(let k=0;k<3;k++){const px=bx+home*(2+k),py=by+k-1;if(S.inB(px,py)&&land[py*w+px]===OPEN)setWall(S,py*w+px,'trench')}},
 tagArea(C,op){const{S,loc,r}=C,rad=op.r||5,tagI=S.tag(op.tag||'churned'),{w,h}=S;for(let y=loc.y-rad;y<=loc.y+rad;y++)for(let x=loc.x-rad;x<=loc.x+rad;x++){if(!S.inB(x,y))continue;const i=y*w+x;if(Math.hypot(x-loc.x,y-loc.y)<=rad&&r()<(op.p||.8)&&S.land[i]===OPEN)S.scar[i]=tagI}},
 wire(C,op){const{S,loc,r}=C,R=loc.site.radius+(op.off||4),cx=loc.site.x,cy=loc.site.y,{w,h}=S,sides=op.sides||2,faces=['n','s','e','w'].sort(()=>r()-.5).slice(0,sides);const put=(x,y)=>{if(!S.inB(x,y))return;const i=y*w+x;if(S.land[i]!==OPEN||isRoadish(S,i)||S.reserved[i]||keepClear(S,x,y))return;setWall(S,i,'trench')};for(const f of faces){for(let a=-R;a<=R;a++){if(((a+R)%9)<2)continue;const x=f==='w'?cx-R:f==='e'?cx+R:cx+a,y=f==='n'?cy-R:f==='s'?cy+R:cy+a;let nearGate=false;for(const g of S.coreGates)if(Math.hypot(x-g.ox,y-g.oy)<4)nearGate=true;if(!nearGate)put(x,y)}}for(const g of S.coreGates)addP(S,C,{type:'prop',kind:op.checkpoint||'checkpoint',x:g.ox,y:g.oy,siteId:g.siteId})},
 blast(C,op){const{S,loc,r}=C,R=loc.site.radius,cx=loc.site.x,cy=loc.site.y,tagI=S.tag('churned'),f=loc.face;for(let y=cy-R+2;y<=cy+R-2;y++)for(let x=cx-R+2;x<=cx+R-2;x++){if(f==='n'&&y>cy-2||f==='s'&&y<cy+2||f==='w'&&x>cx-2||f==='e'&&x<cx+2)continue;if(!S.inB(x,y))continue;const i=y*S.w+x;if(S.reserved[i])continue;if(S.land[i]===WALL&&r()<(op.p||.35)&&S.scar[i]!==S.tag('trench')){S.land[i]=OPEN;S.scar[i]=tagI}else if(S.land[i]===OPEN&&r()<.5)S.scar[i]=tagI}},
 flood(C,op){const{S,loc,r}=C,rad=op.r||7,{w,h}=S;for(let y=loc.y-rad;y<=loc.y+rad;y++)for(let x=loc.x-rad;x<=loc.x+rad;x++){if(!S.inB(x,y))continue;const i=y*w+x;if(Math.hypot(x-loc.x,y-loc.y)>rad||S.land[i]!==OPEN||isRoadish(S,i)||S.reserved[i]||keepClear(S,x,y)||isCore(S,x,y))continue;if(r()<(op.roofs||.14))setWall(S,i,'ruin');else{S.land[i]=WATER;S.ford[i]=0}}refreshFields(S)},
 forest(C,op){const{S,loc,r}=C,rad=op.r||9,{w,h}=S;for(let y=loc.y-rad;y<=loc.y+rad;y++)for(let x=loc.x-rad;x<=loc.x+rad;x++){if(!S.inB(x,y))continue;const i=y*w+x;if(Math.hypot(x-loc.x,y-loc.y)>rad||S.land[i]!==OPEN||isRoadish(S,i)||keepClear(S,x,y))continue;if(r()<.72)S.land[i]=FOREST}for(const e of S.roads){if(e.class>1||e.state!=='open'||e.ring||e.ford)continue;const fromSeat=S.seat?Math.hypot(e.path[0]%w-S.seat.x,(e.path[0]/w|0)-S.seat.y):0;if(fromSeat<rad*2)continue;let k=0,cut=false;for(const i of e.path){if(++k%9<3&&Math.hypot(i%w-loc.x,(i/w|0)-loc.y)<rad*1.6){S.road[i]=0;cut=true}}if(cut)e.state='faded'}},
 site(C,op){const{S,loc,r}=C,s={id:'s'+S.sites.length,kind:op.kind,name:uniq(S,(op.name||'{near}').replace('{near}',loc.site?loc.site.name:'')),x:loc.x,y:loc.y,radius:op.radius||3,importance:op.importance||3,era:C.b.era,state:op.state||'lost',tags:[]};S.sites.push(s);C.loc.site=s;C.vars.site=s.name;{const si=S.idx(s.x,s.y);if(S.road[si]){addEdge(S,{from:s.id,to:(S.seat||S.sites[0]).id,path:[si],name:`${s.name} Lane`,class:1})}else{const p=S.route([si],i=>S.road[i]>0&&i!==si,i=>{if(S.reserved[i])return Infinity;return (S.land[i]===WALL?60:1)*roadBase(S,i)*(S.road[i]?.33:1)});if(p){const e=addEdge(S,{from:s.id,to:(S.seat||S.sites[0]).id,path:p,name:`${s.name} Lane`,class:1});const add=layPath(S,p,1,e.idx);stampRoads(S,add)}}}},
 prop(C,op){const{S,loc,r}=C,n=rint(r,...(Array.isArray(op.n)?op.n:[op.n||1,op.n||1])),rad=op.r||3;for(let k=0;k<n;k++){const p=spotNear(S,loc.x,loc.y,1,rad,r,S.open1);if(p){S.occ[p.i]=1;addP(S,C,{type:'prop',kind:op.kind,x:p.x,y:p.y,siteId:loc.site?loc.site.id:null})}}},
 loot(C,op){const{S,loc,r}=C,n=rint(r,...(Array.isArray(op.n)?op.n:[op.n||1,op.n||1])),rad=op.r||4;for(let k=0;k<n;k++){const p=spotNear(S,loc.x,loc.y,0,rad,r,S.open1);if(p){S.occ[p.i]=1;addP(S,C,{type:'loot',kind:op.kind,x:p.x,y:p.y,size:op.size||1,siteId:loc.site?loc.site.id:null})}}},
 threat(C,op){const{S,loc,r}=C,kind=op.kind,n=op.n||1;for(let k=0;k<n;k++){if(op.foot){const p=findFoot(S,loc.x,loc.y,2,op.r||8,r,op.foot);if(p){reserveFoot(S,p,op.foot);addP(S,C,{type:'threat',kind,x:p.x,y:p.y,size:op.size||1,siteId:loc.site?loc.site.id:null})}}else{const p=spotNear(S,loc.x,loc.y,0,op.r||6,r,S.open0);if(p)addP(S,C,{type:'threat',kind,x:p.x,y:p.y,size:op.size||1,siteId:loc.site?loc.site.id:null})}}},
 sandbags(C,op){const{S,loc,r}=C,{w}=S,len=op.len||4;// two wings either side of the road tile
  const i=S.idx(loc.x,loc.y);let dx=0,dy=0;if(loc.choke&&loc.approach){const P=loc.approach.path,k=P.indexOf(i);if(k>0&&k<P.length-1){const a=P[k+1],b=P[k-1];dx=(a%w)-(b%w);dy=(a/w|0)-(b/w|0)}}if(!dx&&!dy)dy=1;const m=Math.hypot(dx,dy)||1,px=-dy/m,py=dx/m;for(const sgn of [1,-1])for(let o=2;o<2+len;o++){const x=Math.round(loc.x+px*sgn*o),y=Math.round(loc.y+py*sgn*o);if(!S.inB(x,y))continue;const j=y*w+x;if(S.land[j]!==OPEN||isRoadish(S,j)||S.reserved[j]||keepClear(S,x,y))continue;setWall(S,j,op.tag||'trench')}},
 mark(C,op){if(op.tagSite&&C.loc.site)C.loc.site.tags.push(op.tagSite)},
};
function isCore(S,x,y){const R=S.coreRect;return R&&x>=R.x0&&x<=R.x1&&y>=R.y0&&y<=R.y1}
function addP(S,C,p){p.beatId=C?C.b.id:null;S.placements.push(p);return p}
function spotNear(S,x,y,rMin,rMax,r,pred){for(let t=0;t<40;t++){const a=r()*TAU,d=rMin+r()*(rMax-rMin),px=Math.round(x+Math.cos(a)*d),py=Math.round(y+Math.sin(a)*d);if(!S.inB(px,py))continue;const i=py*S.w+px;if(pred(i))return{x:px,y:py,i}}return null}
function footClear(S,x,y,f,opt){const{w}=S;for(let yy=y-1;yy<=y+f;yy++)for(let xx=x-1;xx<=x+f;xx++){if(!S.inB(xx,yy))return false;const j=yy*w+xx;const inside=xx>=x&&xx<x+f&&yy>=y&&yy<y+f;if(inside){if(S.land[j]!==OPEN||S.road[j]||S.ford[j]||S.reserved[j]||S.occ[j])return false}else if(!opt.tight&&S.reserved[j])return false}return true}
function findFoot(S,x,y,rMin,rMax,r,f,opt={}){for(let t=0;t<70;t++){const a=r()*TAU,d=rMin+r()*(rMax-rMin),px=Math.round(x+Math.cos(a)*d)-(f>>1),py=Math.round(y+Math.sin(a)*d)-(f>>1);if(px<2||py<2||px>=S.w-f-2||py>=S.h-f-2)continue;if(S.dStart(px+1,py+1)<(opt.minStart||27))continue;if(S.approachMask&&S.approachMask[py*S.w+px])continue;if(footClear(S,px,py,f,opt))return{x:px,y:py}}return null}
function reserveFoot(S,p,f){for(let yy=p.y;yy<p.y+f;yy++)for(let xx=p.x;xx<p.x+f;xx++){const j=yy*S.w+xx;S.reserved[j]=2;S.occ[j]=1}}
function roadLabel(e){return e?e.name:'the old road'}
function fillText(C,text){const{S,loc,vars}=C;const sub={site:vars.site||(loc.site?loc.site.name:'the district'),road:roadLabel(loc.road||(loc.approach&&loc.approach.roadIds[0]!=null?S.roads[loc.approach.roadIds[0]]:null)),seat:S.seat?S.seat.name:'the town',side:loc.side?SIDES[loc.side]:'north'};return text.replace(/\{(\w+)\}/g,(m,k)=>sub[k]??m)}
function runBeat(S,b,r){const w=b.where;let loc;if(typeof w==='string')loc=WHERE[w]&&WHERE[w](S,b,r,{});else if(w)loc=WHERE[w.type]&&WHERE[w.type](S,b,r,w);else loc={};if(!loc)return false;if(loc._set&&loc.site){loc.x=loc.site.x;loc.y=loc.site.y}const C={S,b,r,loc,vars:{}};for(const op of (b.stamp||[])){const f=OPS[op.op];if(f)f(C,op)}if(b.text)S.chronicle.push({era:b.era,beatId:b.id,siteId:loc.site?loc.site.id:null,text:fillText(C,b.text)});S.beatDone.add(b.id);S.beatsRun.push(b.id);return true}
/* Tidy (Nov 9): the land pass is noise, so it leaves specks of forest, rock and water everywhere, and settled land looked as
   wild as the wilds. This pass makes the land read as used: specks smaller than TIDY.speck tiles go, farms and holdings clear
   fields round them, settlements clear their own ground, and main roads get a clear verge. Ore is never removed. Tuning: TIDY. */
const TIDY={smooth:1,spur:3,fill:6,speck:{1:7,2:6,3:6},fields:6.5,fieldKinds:['farm','holding'],settleKinds:['town','market','hamlet','station','chapel','field hospital','mine','quarry','pithead'],verge:2};
function passTidy(S){const{w,h,n,land,road,reserved}=S;const seen=new Uint8Array(n),comp=[];
 // one majority step: ragged spurs of forest and rock go, notches in a wood fill in, so edges read as drawn rather than sprayed
 for(let it=0;it<TIDY.smooth;it++){const src=land.slice();for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const i=y*w+x;if(reserved[i]||road[i])continue;const L=src[i];let same=0,f=0;
  for(let k=0;k<8;k++){const j=(y+DIR8[k][1])*w+x+DIR8[k][0];if(src[j]===L)same++;if(src[j]===FOREST)f++}
  if((L===FOREST||L===ROCK)&&same<TIDY.spur)land[i]=OPEN;else if(L===OPEN&&f>=TIDY.fill)land[i]=FOREST}}
 for(let i=0;i<n;i++){const L=land[i];if(seen[i]||!TIDY.speck[L])continue;comp.length=0;const st=[i];seen[i]=1;let keep=false;
  while(st.length){const c=st.pop();comp.push(c);if(reserved[c])keep=true;const cx=c%w,cy=c/w|0;for(let k=0;k<4;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx;if(seen[ni]||land[ni]!==L)continue;seen[ni]=1;st.push(ni)}}
  if(!keep&&comp.length<TIDY.speck[L])for(const c of comp)land[c]=OPEN}
 const clear=(cx,cy,R,what)=>{for(let y=Math.floor(cy-R);y<=cy+R;y++)for(let x=Math.floor(cx-R);x<=cx+R;x++){if(!S.inB(x,y))continue;const i=y*w+x;if(reserved[i])continue;const d=Math.hypot(x+.5-cx,y+.5-cy);if(d>R)continue;if(what.includes(land[i]))land[i]=OPEN}};
 for(const s of S.sites){const k=s.kind;if(TIDY.fieldKinds.some(f=>k.includes(f)))clear(s.x+.5,s.y+.5,TIDY.fields*Math.pow(S.mz,.5),[FOREST,ROCK]);
  else if(TIDY.settleKinds.includes(k))clear(s.x+.5,s.y+.5,(s.radius||3)+1.5,[FOREST])}
 for(let i=0;i<n;i++){if(road[i]<2)continue;const x=i%w,y=i/w|0,R=TIDY.verge;for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){if(!S.inB(x+dx,y+dy))continue;const j=(y+dy)*w+x+dx;if(!reserved[j]&&(land[j]===FOREST||land[j]===ROCK)&&Math.abs(dx)+Math.abs(dy)<=R)land[j]=OPEN}}
 if(typeof refreshFields==='function')refreshFields(S)}
function passHistory(S){const r=S.rng('history'),t=S.t;S.beatsRun=[];S.deferred=[];S.open0=i=>S.land[i]===OPEN&&!S.reserved[i];S.open1=i=>S.land[i]===OPEN&&!S.road[i]&&!S.ford[i]&&!S.reserved[i]&&!S.occ[i]&&!S.lootBlock?.[i];
 for(const era of (t.eras||[])){const req=era.required||[],opt=(era.pool||[]).slice();for(const b0 of req){const b=Object.assign({},b0,{era:era.id});if(b.phase==='approaches'){S.deferred.push(b);continue}if(!runBeat(S,b,r)&&b.must)S.fails.push('beat '+b.id)}
  let bud=era.budget||0;while(bud>0&&opt.length){const k=Math.floor(r()*opt.length),b0=opt.splice(k,1)[0];const c=b0.cost||1;if(c>bud)continue;const b=Object.assign({},b0,{era:era.id});if(b.phase==='approaches'){S.deferred.push(b);bud-=c;continue}if(runBeat(S,b,r))bud-=c}}}

/* ---------- pass 6: approaches ---------- */
function stepCost(S,i){if(S.land[i]!==OPEN||S.reserved[i])return Infinity;const rc=S.road[i];return rc===3?.4:rc===2?.55:rc===1?.75:1+(S.nearRough[i]?.35:0)+(S.ford[i]?.5:0)}
function buildRough(S){const{w,h,n,land}=S,R=new Uint8Array(n);for(let i=0;i<n;i++){if(land[i]!==OPEN)continue;const x=i%w,y=i/w|0;let c=0;for(let k=0;k<4;k++){const nx=x+DIR8[k][0],ny=y+DIR8[k][1];if(S.inB(nx,ny)&&land[ny*w+nx]!==OPEN)c++}if(c>=1)R[i]=1}S.nearRough=R}
function passApproaches(S){const{w,h,n,t,land}=S;buildRough(S);const start=[];for(let y=-2;y<=2;y++)for(let x=-2;x<=2;x++){const i=S.idx(S.sx+x,S.sy+y);if(i>=0&&i<n&&land[i]===OPEN)start.push(i)}const flow=S.flow;fieldFrom(S,start,i=>stepCost(S,i),flow);
 const descend=i0=>{const path=[];let c=i0,guard=0;while(c>=0&&flow[c]>0&&guard++<20000){path.push(c);const cx=c%w,cy=c/w|0;let bv=flow[c],bi=-1;for(let k=0;k<8;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx;if(flow[ni]>=bv-1e-6)continue;if(k>=4&&(stepCost(S,cy*w+nx)===Infinity||stepCost(S,ny*w+cx)===Infinity))continue;bv=flow[ni];bi=ni}c=bi}return path};
 const cand=[];for(const side of S.openSides){const rim=rimTiles(S,side).filter(i=>flow[i]<1e9);if(!rim.length)continue;rim.sort((a,b)=>flow[a]-flow[b]);const seeds=[rim[0]];for(const i of rim){if(S.road[i]&&!seeds.includes(i)){if(seeds.every(j=>Math.hypot(j%w-i%w,(j/w|0)-(i/w|0))>8))seeds.push(i)}if(seeds.length>=3)break}for(const i of seeds){const path=descend(i);if(path.length>4)cand.push({side,path})}}
 // major threat sites feed approaches too: their dead come in along the nearest road
 for(const s of S.sites){if(s.importance<(t.majorThreat||6)||s.seat||s.tags.includes('start')||s.tags.includes('gate'))continue;const i=S.idx(s.x,s.y);if(flow[i]>=1e9)continue;const path=descend(i);if(path.length>4){const side=Math.abs(s.x-S.sx)>Math.abs(s.y-S.sy)?(s.x<S.sx?'w':'e'):(s.y<S.sy?'n':'s');cand.push({side,path,fromSite:s.id})}}
 if(S.seat){const near=S.coreGates.map(g=>S.idx(clamp(g.ox,0,w-1),clamp(g.oy,0,h-1))).filter(i=>flow[i]<1e9).sort((a,b)=>flow[b]-flow[a])[0];if(near!=null){const path=descend(near);if(path.length>4){const side=Math.abs(S.seat.x-S.sx)>Math.abs(S.seat.y-S.sy)?(S.seat.x<S.sx?'w':'e'):(S.seat.y<S.sy?'n':'s');cand.push({side,path,fromSite:S.seat.id})}}}
 cand.forEach(c=>{c.set=new Set(c.path);c.tr=c.path.reduce((a,i)=>a+S.traffic[i],0)/c.path.length});cand.sort((a,b)=>b.tr-a.tr);
 const keep=[];for(const c of cand){let dup=false;for(const k of keep){if(k.side!==c.side&&!(c.fromSite&&k.fromSite))continue;let sh=0;for(const i of c.path)if(k.set.has(i))sh++;if(sh/Math.min(c.path.length,k.path.length)>.72){dup=true;break}}if(!dup)keep.push(c)}
 // every open edge keeps at least one approach
 for(const side of S.openSides)if(!keep.some(c=>c.side===side&&!c.fromSite)){const c=cand.find(q=>q.side===side&&!q.fromSite);if(c)keep.push(c)}
 S.approaches=keep.map((c,ix)=>{const roadCount=new Map();for(const i of c.path){const r=S.roadId[i];if(r>=0)roadCount.set(r,(roadCount.get(r)||0)+1)}const ids=[...roadCount.keys()].sort((a,b)=>roadCount.get(b)-roadCount.get(a));const main=ids.length&&roadCount.get(ids[0])>c.path.length*.2?S.roads[ids[0]]:null,base=main?main.name:'the open ground',name=`${base}, from the ${SIDES[c.side]}`;const a={id:'a'+ix,name,short:base,fromEdge:c.side,fromSite:c.fromSite||null,path:c.path,roadIds:ids.slice(0,4),chokepoints:[],weight:Math.round((1+c.tr)*10)/10};a.chokepoints=findChokes(S,c.path);return a});
 S.approachMask=new Uint8Array(n);for(const a of S.approaches){if(a.fromSite)continue;for(const i of a.path){const x=i%w,y=i/w|0;for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){if(S.inB(x+dx,y+dy))S.approachMask[(y+dy)*w+x+dx]=1}}}
 const r=S.rng('approachBeats');for(const b of S.deferred)runBeat(S,b,r)}
function findChokes(S,path){const{w,land}=S,out=[];const width=(i,dx,dy)=>{const x=i%w,y=i/w|0;let c=1;for(const sg of [1,-1])for(let o=1;o<8;o++){const nx=x+dx*sg*o,ny=y+dy*sg*o;if(!S.inB(nx,ny)||land[ny*w+nx]!==OPEN)break;c++}return c};let last=-99;const trenchTag=S.tags.indexOf('trench');
 for(let k=2;k<path.length-2;k++){const i=path[k],x=i%w,y=i/w|0;if(k-last<8)continue;let kind=null;if(S.ford[i])kind=S.sites.some(s=>s.tags.includes('crossing')&&s.state==='intact'&&Math.hypot(s.x-x,s.y-y)<3)?'bridge':'ford';else if(S.cut[i])kind='gap';else{let trenchNear=false;if(trenchTag>0)for(let dy=-3;dy<=3&&!trenchNear;dy++)for(let dx=-3;dx<=3;dx++)if(S.inB(x+dx,y+dy)&&S.scar[(y+dy)*w+x+dx]===trenchTag){trenchNear=true;break}const a=path[k+1],b=path[k-1],dx=(a%w)-(b%w),dy=(a/w|0)-(b/w|0),wd=Math.max(1,Math.min(width(i,-dy,dx),width(i,dy,-dx)));const ww=width(i,Math.sign(-dy),Math.sign(dx));if(ww<=4||(trenchNear&&ww<=7))kind=trenchNear?'trench':'narrow'}if(kind){out.push({x,y,kind,d:Math.round(S.dStart(x,y)*10)/10});last=k}}
 return out}

/* ---------- pass 7: population ---------- */
function pass7Population(S){const{w,h,t,ctx}=S,r=S.rng('population'),T=t.population||{},dist=t.districts||[],budget=ctx.budget||{};
 const kinds=T.kinds||{major:'hamlet',strong:'stronghold',pack:'pack',wander:'wander',cache:'cache'};
 const hamletGoal=Math.max(1,Math.round((budget.hamlets||6)*(T.hamletMul||1)));S.hamletGoal=hamletGoal;
 const distIds=dist.map(d=>d.id),tileByDist=new Map();for(const d of dist)tileByDist.set(d.id,0);for(let i=0;i<S.n;i++){const d=S.districts[S.district[i]];if(tileByDist.has(d)&&S.land[i]===OPEN)tileByDist.set(d,tileByDist.get(d)+1)}
 const present=dist.filter(d=>(tileByDist.get(d.id)||0)>30);let lootShare=0;for(const d of present)lootShare+=d.loot;
 // 1. blockers on the gates
 const hamletsPlaced=()=>S.placements.filter(p=>p.type==='threat'&&(p.kind===kinds.major||p.kind===kinds.strong)||p.type==='blocker').length;
 for(const g of S.coreGates)S.placements.push({type:'blocker',kind:kinds.major,x:g.x,y:g.y,size:1,siteId:g.siteId,beatId:'gate',gap:{x:g.x,y:g.y,w:3,side:g.side},behind:'core'});
 const addH=(x,y,siteId,beatId,kind)=>{reserveFoot(S,{x,y},3);S.placements.push({type:'threat',kind:kind||kinds.major,x,y,size:1,siteId,beatId:beatId||'population'})};
 // 2. hamlets inside the core: on its squares, as a share of the budget
 const coreGoal=S.seat&&S.coreSquares.length?Math.min(S.coreSquares.length,Math.ceil(hamletGoal*(T.coreHamletShare??.3))):0,sq=S.coreSquares.slice().sort(()=>r()-.5);let placedCore=0;for(const c of sq){if(placedCore>=coreGoal)break;if(!footClear(S,c.x,c.y,3,{tight:true}))continue;addH(c.x,c.y,S.seat.id,'population');placedCore++}
 // 3. the rest at sites, by district weight
 const siteList=S.sites.filter(s=>!s.tags.includes('crossing')&&!s.tags.includes('start')&&!s.tags.includes('gate')&&!s.seat);const rowOf=s=>{const d=(t.districtOf||{})[s.kind]||(t.districtOf||{}).default;return dist.find(q=>q.id===(d&&d[0]))||{hamlet:.2,id:'wilds',loot:.2,threat:.2}};
 const order=siteList.map(s=>({s,w:(rowOf(s).hamlet||.1)*s.importance*(.5+r())})).sort((a,b)=>b.w-a.w);
 for(const{s}of order){if(hamletsPlaced()>=hamletGoal)break;const p=findFoot(S,s.x,s.y,3,14,r,3);if(p)addH(p.x,p.y,s.id,'population')}
 // fallback: any distant open spot beside a road, named for the nearest site
 for(let g=0;g<3000&&hamletsPlaced()<hamletGoal;g++){const i=rint(r,0,S.n-1),x=i%w,y=i/w|0;if(S.road[i]||S.land[i]!==OPEN)continue;const p=findFoot(S,x,y,0,1,r,3);if(!p)continue;let bad=false;for(const q of S.placements)if(q.type!=='prop'&&(q.kind===kinds.major||q.kind===kinds.strong)&&Math.hypot(q.x-p.x,q.y-p.y)<9){bad=true;break}if(!bad)addH(p.x,p.y,siteNear(S,p.x,p.y).id,'fill')}
 // 4. caches, by district share, near the sites and roads of that district
 const cachesTotal=budget.caches||40,beatsLoot=S.placements.filter(p=>p.type==='loot').length;let cachesLeft=Math.max(0,cachesTotal-beatsLoot);const tiles=d=>d.id;
 const lootTable=T.loot||{},row=(d)=>lootShare?d.loot/lootShare:0;
 const sitesIn=id=>S.sites.filter(s=>{const dd=(t.districtOf||{})[s.kind]||(t.districtOf||{}).default;return dd&&dd[0]===id&&!s.tags.includes('crossing')&&!s.tags.includes('start')&&!s.tags.includes('gate')});
 for(const d of present){const n=Math.round(row(d)*cachesLeft),inD=sitesIn(d.id).concat(d.id==='core'&&S.seat?[S.seat]:[]);let made=0;for(let g=0;g<n*6&&made<n;g++){const s=inD.length?pick(r,inD):null,rad=s?(s.radius+6):8;let p=null;if(d.id==='core'&&S.coreRect){const R=S.coreRect;for(let t2=0;t2<30&&!p;t2++){const x=rint(r,R.x0+2,R.x1-2),y=rint(r,R.y0+2,R.y1-2),i=y*w+x;if(S.land[i]===OPEN&&!S.occ[i]&&!S.reserved[i])p={x,y,i}}}else if(s){p=spotNear(S,s.x,s.y,0,rad,r,S.open1)}if(!p)for(let t2=0;t2<40&&!p;t2++){const i=rint(r,0,S.n-1);if(S.districts[S.district[i]]===d.id&&S.open1(i)&&S.dStart(i%w,i/w|0)>=12)p={x:i%w,y:i/w|0,i}}if(!p)continue;S.occ[p.i]=1;const kindsL=(lootTable[s?s.kind:d.id]||lootTable[d.id]||lootTable.default||['cache']);S.placements.push({type:'loot',kind:pick(r,kindsL),x:p.x,y:p.y,size:d.size||1,siteId:(s||siteNear(S,p.x,p.y)).id,beatId:'population'});made++}}
 // 5. threat packs (scaled to the game's count by the adapter) where people were; wanderers on the roads
 const packs=(d,count)=>{const inD=sitesIn(d.id).concat(d.id==='core'&&S.seat?[S.seat]:[]);for(let k=0;k<count;k++){const s=inD.length?pick(r,inD):siteNear(S,rint(r,8,w-9),rint(r,8,h-9));if(!s)continue;let p=spotNear(S,s.x,s.y,1,s.radius+8,r,S.open0);if(!p)continue;if(S.dStart(p.x,p.y)<21)continue;S.placements.push({type:'threat',kind:kinds.pack,x:p.x,y:p.y,size:1+((r()*3)|0),siteId:s.id,beatId:'population'})}};
 for(const d of present)packs(d,Math.round(d.threat*(T.packsPer||18)*S.cz*S.cz));
 // wanderers: spread along roads between hamlets
 const roadsL=S.roads.filter(e=>e.state==='open'&&e.path.length>12);const nw=Math.round((T.wanderers||40)*S.cz*S.cz);for(let k=0;k<nw&&roadsL.length;k++){const e=pick(r,roadsL),i=e.path[(r()*e.path.length)|0],x=i%w,y=i/w|0;if(S.dStart(x,y)<22)continue;S.placements.push({type:'threat',kind:kinds.wander,x,y,size:1+((r()*2)|0),siteId:siteNear(S,x,y).id,beatId:'population',roadId:e.idx})}}

/* ---------- pass 8: validation and repair ---------- */
function floodBlockers(S){const{n,w,h,land}=S,seen=new Uint8Array(n),st=[S.sIdx];seen[S.sIdx]=1;while(st.length){const c=st.pop(),cx=c%w,cy=c/w|0;for(let k=0;k<4;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx;if(seen[ni]||land[ni]!==OPEN)continue;seen[ni]=1;st.push(ni)}}return seen}
function ringOf(S,F,x,y){const d=F[y*S.w+x]/S.mz;return d<22?0:d<42?1:d<62?2:3}
function passValidate(S){const{n,w,h,t,land,reserved}=S,r=S.rng('validate'),T=t.population||{},kinds=T.kinds||{major:'hamlet',strong:'stronghold',pack:'pack',wander:'wander',cache:'cache'},fails=S.fails,hamletKinds=new Set([kinds.major,kinds.strong]);
 const coreI=S.distOf('core');
 // reachability: flood treats blocker footprints as passable; unreached open land becomes forest unless loot needs it, then a gap is opened
 let seen=floodBlockers(S);const breach=(pI)=>{const p=S.route([pI],i=>seen[i]===1,i=>land[i]===OPEN?1:land[i]===WATER?8:land[i]===WALL?4:6);if(p){for(const i of p){if(land[i]===WATER){land[i]=OPEN;S.ford[i]=1}else if(land[i]!==OPEN&&!reserved[i])land[i]=OPEN}seen=floodBlockers(S);S.repairs.opened++}};
 S.repairs={opened:0,moved:0,added:0,blob:0};
 for(const p of S.placements){if(p.type!=='loot'&&!(p.type==='threat'&&hamletKinds.has(p.kind)))continue;const i=p.y*w+p.x;if(!seen[i]&&land[i]===OPEN)breach(i)}
 for(const k of S.openSides){let open=rimTiles(S,k).filter(i=>seen[i]).length;if(open<4){const rim=rimTiles(S,k).filter(i=>land[i]===OPEN),ser=rim.length?rim:rimTiles(S,k),mid=ser[ser.length>>1];breach(mid);const x=mid%w,y=mid/w|0;for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){if(S.inB(x+dx,y+dy)){const j=(y+dy)*w+x+dx;if(land[j]!==OPEN){if(land[j]===WATER)S.ford[j]=1;land[j]=OPEN}}}seen=floodBlockers(S)}}
 for(let i=0;i<n;i++){if(land[i]===OPEN&&!seen[i]&&!reserved[i]&&!S.occ[i]){land[i]=FOREST;S.ford[i]=0;S.road[i]=0}}
 // starting resources
 const within=(lc,R)=>{let c=0;for(let y=Math.floor(S.sy-R);y<=S.sy+R;y++)for(let x=Math.floor(S.sx-R);x<=S.sx+R;x++)if(S.inB(x,y)&&land[y*w+x]===lc&&S.dStart(x,y)<R)c++;return c};
 const startCheck=[[FOREST,8],[ROCK,4],[WATER,3],[ORE,3]];for(const[lc,need]of startCheck){if(within(lc,26)<need){S.ring(r()*TAU,14+r()*6,2.6,lc);S.repairs.blob++}}
 let clear=0,tot=0;const G9=9+S.ck;for(let y=Math.floor(S.sy-G9);y<=S.sy+G9;y++)for(let x=Math.floor(S.sx-G9);x<=S.sx+G9;x++){if(S.dStart(x,y)<G9){tot++;if(land[y*w+x]===OPEN)clear++;else if(S.road[y*w+x]===0){land[y*w+x]=OPEN;clear++}}}
 seen=floodBlockers(S);
 // edge openness
 for(const k of S.openSides){const open=rimTiles(S,k).filter(i=>seen[i]);if(open.length<4)fails.push('edge '+k)}
 // reach map for rings (blockers passable)
 buildRough(S);const reachF=new Float32Array(n);fieldFrom(S,[S.sIdx],i=>land[i]===OPEN?1:Infinity,reachF);
 const rings=[{loot:0,lootV:0,threat:0,buildable:0,blockers:0,tiles:0},{loot:0,lootV:0,threat:0,buildable:0,blockers:0,tiles:0},{loot:0,lootV:0,threat:0,buildable:0,blockers:0,tiles:0},{loot:0,lootV:0,threat:0,buildable:0,blockers:0,tiles:0}];
 const rg=(x,y)=>{const f=reachF[y*w+x];const d=f/S.mz;return d<22?0:d<42?1:d<62?2:3};
 for(let i=0;i<n;i++){if(reachF[i]>=1e9)continue;const q=rings[rg(i%w,i/w|0)];q.tiles++;if(land[i]===OPEN&&!S.road[i]&&!S.ford[i]&&!reserved[i])q.buildable++}
 const lootV=p=>(p.size||1);let lootTot=0,lootCore=0;for(const p of S.placements){if(p.type==='loot'){const q=rings[rg(p.x,p.y)];q.loot++;q.lootV+=lootV(p);lootTot+=lootV(p);if(S.district[p.y*w+p.x]===coreI)lootCore+=lootV(p)}else if(p.type==='threat'){const q=rings[rg(p.x,p.y)];q.threat+=hamletKinds.has(p.kind)?3:(p.size||1)*.3}else if(p.type==='blocker'){const q=rings[rg(p.x,p.y)];q.blockers++;q.threat+=3}}
 // core share: move distant loot into the core if short
 if(S.seat&&coreI>=0&&lootTot>0&&T.coreLootShare){const need=T.coreLootShare,sq=S.coreRect,streets=[];if(sq)for(let y=sq.y0+2;y<=sq.y1-2;y++)for(let x=sq.x0+2;x<=sq.x1-2;x++){const i=y*w+x;if(land[i]===OPEN&&!S.occ[i]&&!reserved[i]&&seen[i])streets.push({x,y,i})}streets.sort(()=>r()-.5);let safety=0;const movable=S.placements.filter(p=>p.type==='loot'&&S.district[p.y*w+p.x]!==coreI&&p.beatId==='population').sort((a,b)=>(a.size||1)-(b.size||1));while(lootCore/lootTot<need&&streets.length&&movable.length&&safety++<400){const p=movable.pop(),s=streets.pop();S.occ[p.y*w+p.x]=0;lootCore-=0;const ov=lootV(p);rings[rg(p.x,p.y)].lootV-=ov;p.x=s.x;p.y=s.y;p.siteId=S.seat.id;S.occ[s.i]=1;const rg2=rings[rg(s.x,s.y)];rg2.lootV+=ov;lootCore+=ov;S.repairs.moved++}
 }
 // "first ring is safe enough to build in"
 const safe=S.placements.filter(p=>(p.type==='threat'||p.type==='blocker')&&hamletKinds.has(p.kind)&&S.dStart(p.x,p.y)<(p.type==='blocker'?20:24));if(safe.length)fails.push('hamlet too close');
 // hamlets
 const ham=S.placements.filter(p=>(p.type==='blocker')||(p.type==='threat'&&hamletKinds.has(p.kind)));const hamletCount=ham.length;if(hamletCount<S.hamletGoal)fails.push(`hamlets ${hamletCount}/${S.hamletGoal}`);
 let coreHam=0;for(const p of ham){if(S.seat&&isCore(S,p.x+1,p.y+1))coreHam++}
 const coreArea=S.coreRect?(S.coreRect.x1-S.coreRect.x0+1)*(S.coreRect.y1-S.coreRect.y0+1):1,coreDensity=coreHam/coreArea,totArea=n,meanDensity=hamletCount/totArea;
 if(S.seat&&coreI>=0&&T.coreLootShare){if(lootCore/lootTot<T.coreLootShare-.0001)fails.push(`core loot ${(lootCore/lootTot).toFixed(2)}`);if(coreDensity<2*meanDensity)fails.push('core hamlet density')}
 // gates
 if(S.seat&&T.gatesRequired!==false&&S.coreRect){if(S.coreGates.length<2||S.coreGates.length>4)fails.push('gates '+S.coreGates.length);for(const g of S.coreGates){if(!S.placements.some(p=>p.type==='blocker'&&p.x===g.x&&p.y===g.y))fails.push('gate without blocker')}}
 // roads
 for(const s of S.sites){if(s.tags.includes('crossing')||s.tags.includes('gate'))continue;if(!S.road[S.idx(s.x,s.y)]&&!S.roads.some(e=>e.from===s.id||e.to===s.id))fails.push('site without road '+s.kind)}
 for(const e of S.roads){if(!e.from||!e.to)fails.push('road without ends')}
 // approaches
 const stat=fails.length;for(const k of S.openSides)if(!S.approaches.some(a=>a.fromEdge===k&&!a.fromSite))fails.push('no approach '+k);
 const mainApps=S.approaches.filter(a=>!a.fromSite);let distinct=false;for(let a=0;a<mainApps.length&&!distinct;a++)for(let b=a+1;b<mainApps.length;b++){const A=new Set(mainApps[a].path);let sh=0;for(const i of mainApps[b].path)if(A.has(i))sh++;if(sh/Math.min(mainApps[a].path.length,mainApps[b].path.length)<.5){distinct=true;break}}if(!distinct)fails.push('approaches not distinct');
 for(const a of mainApps){if(!a.chokepoints.some(c=>c.d>12))fixChoke(S,a,r)}
 for(const a of mainApps)if(!a.chokepoints.some(c=>c.d>12))fails.push('no choke '+a.id);
 // each approach walled off along its length: its edge must still reach the start (roads are a preference, never a rail)
 for(const a of mainApps){const wall=new Uint8Array(n);for(const i of a.path){const x=i%w,y=i/w|0;if(S.dStart(x,y)<=9.5+S.ck)continue;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){if(S.inB(x+dx,y+dy))wall[(y+dy)*w+x+dx]=1}}
  const seen2=new Uint8Array(n),q=[S.sIdx];seen2[S.sIdx]=1;for(let qi=0;qi<q.length;qi++){const c=q[qi],cx=c%w,cy=c/w|0;for(let k=0;k<4;k++){const nx=cx+DIR8[k][0],ny=cy+DIR8[k][1];if(!S.inB(nx,ny))continue;const ni=ny*w+nx;if(seen2[ni]||land[ni]!==OPEN||S.reserved[ni]||wall[ni])continue;seen2[ni]=1;q.push(ni)}}
  const rim=rimTiles(S,a.fromEdge),rimSet=new Set(rim);if(!rim.some(i=>seen2[i])){const p=S.route([S.sIdx],i=>rimSet.has(i)&&!wall[i],i=>{if(wall[i]||S.reserved[i])return Infinity;return land[i]===OPEN?1:land[i]===WATER?12:land[i]===WALL?9:6});if(p){for(const i of p){if(land[i]===WATER){land[i]=OPEN;S.ford[i]=1}else if(land[i]!==OPEN)land[i]=OPEN}S.repairs.opened++}else fails.push('edge sealed '+a.fromEdge)}}
 const coreDist=S.coreGates&&S.coreGates.length?Math.round(Math.min(...S.coreGates.map(g=>reachF[S.idx(g.ox,g.oy)]))):null;if(coreDist!=null&&coreDist<1e9){const[a,b]=(T.coreRoad||[20,58]);if(coreDist<a*S.mz*.9||coreDist>b*S.mz*1.1)fails.push(`core road ${coreDist}`)}
 // rising rings
 const dens=rings.map(q=>({l:q.tiles?q.lootV/q.tiles:0,t:q.tiles?q.threat/q.tiles:0}));let peak=0;for(let k=1;k<4;k++)if(dens[k].l>dens[peak].l)peak=k;
 {const packK=kinds.pack;for(let k=peak;k>=1;k--){let guard=0;while(dens[k].t<dens[k-1].t*.6&&guard++<60&&rings[k].tiles>=80){const movable=S.placements.filter(p=>p.type==='threat'&&p.kind===packK&&rg(p.x,p.y)===k-1);if(!movable.length)break;let spot=null;for(let t2=0;t2<60&&!spot;t2++){const i=rint(r,0,n-1),x=i%w,y=i/w|0;if(reachF[i]<1e9&&rg(x,y)===k&&land[i]===OPEN&&!reserved[i]&&!S.occ[i])spot={x,y}}if(!spot)break;const p=pick(r,movable),sz=(p.size||1)*.3;rings[k-1].threat-=sz;p.x=spot.x;p.y=spot.y;p.siteId=siteNear(S,spot.x,spot.y).id;p.beatId=p.beatId+'+repair';rings[k].threat+=sz;dens[k].t=rings[k].threat/rings[k].tiles;dens[k-1].t=rings[k-1].threat/rings[k-1].tiles;S.repairs.moved++}}}
 for(let k=1;k<=peak;k++){if(rings[k].tiles<80||rings[k-1].tiles<80)continue;if(dens[k].l<dens[k-1].l*.6&&lootTot>2)fails.push('loot falls ring'+k);if(dens[k].t<dens[k-1].t*.6)fails.push('threat falls ring'+k)}
 if(S.flowDirty){}
 S.metrics={rings:rings.map((q,k)=>({ring:k,loot:q.loot,lootV:Math.round(q.lootV*10)/10,threat:Math.round(q.threat*10)/10,buildable:q.buildable,blockers:q.blockers})),hamlets:hamletCount,hamletGoal:S.hamletGoal,caches:S.placements.filter(p=>p.type==='loot').length,coreLootShare:S.seat&&lootTot?Math.round(lootCore/lootTot*100)/100:null,coreHam,coreDensityRatio:Math.round(coreDensity/(meanDensity||1)*10)/10,gates:S.coreGates.length,approaches:mainApps.length,chokes:mainApps.reduce((a,q)=>a+q.chokepoints.length,0),seatRoad:coreDist,repairs:S.repairs,fails:fails.slice(),ok:fails.length===0}}
function fixChoke(S,a,r){const P=a.path,w=S.w;let bestK=-1,bs=-1;for(let k=Math.floor(P.length*.2);k<P.length*.85;k++){const i=P[k],x=i%w,y=i/w|0,d=S.dStart(x,y);if(d<16||S.ford[i])continue;const sc=(S.road[i]>=2?2:1)+r()*1+(d>20&&d<40?1:0);if(sc>bs){bs=sc;bestK=k}}if(bestK<0)return;const i=P[bestK],x=i%w,y=i/w|0,a2=P[Math.min(bestK+1,P.length-1)],b=P[Math.max(bestK-1,0)],dx=(a2%w)-(b%w),dy=(a2/w|0)-(b/w|0),m=Math.hypot(dx,dy)||1,px=-dy/m,py=dx/m;let n=0;for(const sg of [1,-1])for(let o=2;o<7;o++){const qx=Math.round(x+px*sg*o),qy=Math.round(y+py*sg*o);if(!S.inB(qx,qy))continue;const j=qy*w+qx;if(S.land[j]!==OPEN||S.road[j]||S.ford[j]||S.reserved[j]||S.dStart(qx,qy)<13)continue;S.land[j]=WALL;S.scar[j]=S.tag('trench');n++}if(n){const c={x,y,kind:'checkpoint',d:Math.round(S.dStart(x,y)*10)/10};a.chokepoints.push(c);S.placements.push({type:'prop',kind:'checkpoint',x,y,siteId:siteNear(S,x,y).id,beatId:'repair'});S.repairs.added++}}

/* ---------- public ---------- */
function generate(o){const t0=Date.now(),S=makeState(o);
 passLand(S);pass2Settlement(S);pass3Roads(S);pass4Districts(S);passTidy(S);passHistory(S);passApproaches(S);pass7Population(S);passValidate(S);
 if(S.approaches&&S.approaches.length){const main=S.approaches.filter(a=>!a.fromSite);S.chronicle.push({era:'present',beatId:null,siteId:null,text:`The dead come by ${main.map(a=>a.short).slice(0,2).join(' and ')}.`})}
 return{seed:o.seed,w:S.w,h:S.h,template:o.template.id,grids:{land:S.land,ford:S.ford,district:S.district,roadClass:S.road,scarTag:S.scar,flow:S.flow,reserved:S.reserved,tvar:S.tvar},districts:S.districts,tags:S.tags,sites:S.sites.map(s=>({id:s.id,kind:s.kind,name:s.name,x:s.x,y:s.y,radius:s.radius,importance:s.importance,era:s.era,state:s.state,tags:s.tags,seat:!!s.seat})),roads:S.roads.map(e=>({id:e.id,name:e.name,from:e.from,to:e.to,class:e.class,path:e.path,traffic:e.traffic,state:e.state})),approaches:S.approaches,placements:S.placements,chronicle:S.chronicle,metrics:S.metrics,start:{x:S.sx,y:S.sy},ms:Date.now()-t0}}
return{generate,OPEN,FOREST,ROCK,WATER,WALL,ORE,LAND_NAMES,SIDES,register:{where:(k,f)=>{WHERE[k]=f},op:(k,f)=>{OPS[k]=f}}};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=MapKit;
