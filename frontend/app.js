'use strict';
const paths = {
 waves:'M3 8c3-4 6 4 9 0s6 4 9 0M3 14c3-4 6 4 9 0s6 4 9 0M3 20c3-4 6 4 9 0s6 4 9 0',
 dashboard:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
 list:'M8 5h13M8 12h13M8 19h13M3 5h.1M3 12h.1M3 19h.1',
 document:'M14 2H5v20h14V7zM14 2v6h5M8 12h8M8 16h6',
 layers:'m12 3 10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5',
 info:'M12 17v-5M12 7h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
 refresh:'M20 7a9 9 0 1 0 1 9M20 2v6h-6',
 search:'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
 calendar:'M3 5h18v16H3zM7 2v6M17 2v6M3 11h18',
 filter:'M3 5h18M6 12h12M9 19h6',
 arrow:'M5 12h14m-5-5 5 5-5 5',
 focus:'M9 3H3v6M15 3h6v6M21 15v6h-6M3 15v6h6M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
 download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
 close:'m6 6 12 12M6 18 18 6',
 clock:'M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 alert:'m12 3 10 18H2zM12 9v5M12 17h.01',
 check:'m5 12 4 4L19 6',
 external:'M14 3h7v7M21 3 10 14M10 3H3v18h18v-7',
 route:'M6 3v18M18 3v18M12 3v4M12 10v4M12 17v4',
 database:'M21 5c0 4-18 4-18 0s18-4 18 0v14c0 4-18 4-18 0V5M3 12c0 4 18 4 18 0'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.info}"/></svg>`;
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fold = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const safeURL = value => {try {const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u.href:'';}catch{return '';}};
const format = (value, options) => {const d=new Date(value);return value && Number.isFinite(+d)?new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',...options}).format(d):'Não informado';};
const time = value => format(value,{hour:'2-digit',minute:'2-digit'});
const date = value => format(value,{day:'2-digit',month:'2-digit',year:'numeric'});
const shortDate = value => format(value,{day:'2-digit',month:'2-digit'});
const dayKey = value => {const d=new Date(value);if(!value||!Number.isFinite(+d))return '';const p=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d);return ['year','month','day'].map(k=>p.find(x=>x.type===k).value).join('-');};
const minutes = value => {if(!value||!Number.isFinite(+new Date(value)))return null;const p=new Intl.DateTimeFormat('en-GB',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(value)).split(':').map(Number);return p[0]*60+p[1];};
const duration = r => r.inicio_evento&&r.fim_evento && Number.isFinite(+new Date(r.fim_evento)-new Date(r.inicio_evento)) ? Math.max(0,Math.round((new Date(r.fim_evento)-new Date(r.inicio_evento))/60000)):null;
const prettyStreet = value => String(value||'Via não informada').toLocaleLowerCase('pt-BR').replace(/(^|\s)\S/g,c=>c.toUpperCase()).replace(/^Av /,'Av. ').replace(/^R /,'R. ');
const isBlocked = r => fold(r.status_via).includes('intransit');
const fusionLabel = status => ({CONFIRMADO_DUPLO:'Confirmação dupla',APENAS_CGE:'Somente CGE',APENAS_MIDIA:'Somente mídia',NAO_PROCESSADO:'Não processado'}[status] || status || 'Não informado');
const pill = r => `<span class="pill ${isBlocked(r)?'orange':'green'}">${escapeHTML(r.status_via||'Não informado')}</span>`;
const state = {data:null,rows:[],page:'overview',map:null,eventLayer:null,newsLayer:null,networkLayer:null,showNetwork:false,selected:null};
let toastTimer;
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3500);}
const pages = {
 overview:['Visão geral','Cada ocorrência, <span>mais contexto.</span>','Explore os impactos das chuvas em Itaquera, conectando registros oficiais e notícias.'],
 records:['Ocorrências','O detalhe de <span>cada ocorrência.</span>','Consulte horários, condições das vias e evidências nos registros do projeto.'],
 sources:['Fontes e notícias','Toda evidência <span>tem uma origem.</span>','Conheça os textos, os registros institucionais e os dados que sustentam a análise.'],
 pipeline:['Pipeline de dados','Dos dados brutos <span>à leitura integrada.</span>','Acompanhe a disponibilidade das etapas de processamento no seu projeto.'],
 methodology:['Metodologia','Mais transparência. <span>Melhor interpretação.</span>','Entenda os critérios de cruzamento e os limites deste recorte de pesquisa.']
};
function navigate(){
 const page=location.hash.slice(1);state.page=pages[page]?page:'overview';const content=pages[state.page];
 document.querySelectorAll('.page').forEach(el=>el.hidden=el.id!==state.page);
 document.querySelectorAll('[data-page]').forEach(el=>{el.classList.toggle('active',el.dataset.page===state.page);if(el.dataset.page===state.page)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 $('breadcrumb').textContent=content[0];$('page-title').innerHTML=content[1];$('page-description').textContent=content[2];
 $('filters').hidden=!['overview','records'].includes(state.page);
 document.title=`${content[0]} · Flood Fusion SP`;
 if(state.map && state.page==='overview')setTimeout(()=>state.map.invalidateSize(),50);
}
function baseRows(){return $('dataset').value==='fusion'?state.data.fused:state.data.records;}
function updateDates(){
 const old=$('date').value;const days=[...new Set(baseRows().map(r=>dayKey(r.inicio_evento)).filter(Boolean))].sort();
 $('date').innerHTML='<option value="">Todo o período</option>'+days.map(d=>`<option value="${d}">${date(d+'T12:00:00-03:00')}</option>`).join('');
 if(days.includes(old))$('date').value=old;
}
function filterRows(){
 const query=fold($('search').value),day=$('date').value,status=$('status').value;
 state.rows=baseRows().filter(r=>(!day||dayKey(r.inicio_evento)===day)&&(!status||r.status_via===status)&&(!query||fold(`${r.logradouro} ${r.referencia||''} ${r.fontes||''}`).includes(query)));
 renderMetrics();renderTables();renderTimeline();renderMap();
}
function renderMetrics(){
 const rows=state.rows,blocked=rows.filter(isBlocked),streets=new Set(rows.map(r=>fold(r.logradouro))).size;
 const completed=blocked.map(duration).filter(n=>n!==null),avg=completed.length?Math.round(completed.reduce((a,b)=>a+b,0)/completed.length):null;
 const items=[
 ['Registros no recorte',String(rows.length).padStart(2,'0'),'database','accent',`${rows.length===1?'ocorrência encontrada':'ocorrências encontradas'}`],
 ['Registros intransitáveis',String(blocked.length).padStart(2,'0'),'alert','danger','registros de obstrução'],
 ['Vias distintas',String(streets).padStart(2,'0'),'route','','logradouros no recorte'],
 ['Duração média',avg===null?'—':`${avg}<span style="font-size:14px;letter-spacing:0;margin-left:5px">min</span>`,'clock','','entre obstruções com término']];
 $('metrics').innerHTML=items.map(([label,value,i,c,footer])=>`<article class="metric ${c}"><span class="metric-label">${label}</span><span class="metric-icon">${icon(i)}</span><div class="metric-value">${value}</div><div class="metric-bottom"><span class="tiny-dot"></span>${footer}</div></article>`).join('');
}
function tableHTML(){
 const rows=state.rows;
 if(!rows.length)return `<div class="empty">${icon('search')}<strong>${$('dataset').value==='fusion'&&!state.data.fusion_available?'A fusão ainda não foi gerada.':'Nenhum registro neste recorte.'}</strong>${$('dataset').value==='fusion'&&!state.data.fusion_available?'O painel reconhecerá o GeoJSON final assim que ele estiver disponível.':'Ajuste a data, a condição ou o termo de busca.'}</div>`;
 return `<div class="table-wrap"><table><thead><tr><th>Via / referência</th><th>Data</th><th>Janela do evento</th><th>Condição</th><th>${$('dataset').value==='fusion'?'Validação cruzada':'Fonte'}</th><th>Duração</th></tr></thead><tbody>${rows.map(r=>`<tr><td><button class="street-button" data-record="${escapeHTML(r.id)}">${icon('pin')}${escapeHTML(prettyStreet(r.logradouro))}</button>${r.referencia?`<small>${escapeHTML(prettyStreet(r.referencia))}</small>`:''}</td><td>${shortDate(r.inicio_evento)}</td><td>${time(r.inicio_evento)} <span style="color:#a9b2a0">—</span> ${time(r.fim_evento)}</td><td>${pill(r)}</td><td><span class="pill neutral">${escapeHTML(r.kind==='fusion'?fusionLabel(r.status_fusao):r.fontes)}</span></td><td>${duration(r)===null?'Em aberto':`${duration(r)} min`}</td></tr>`).join('')}</tbody></table></div><div class="table-footer"><span>${rows.length} de ${baseRows().length} registros · horários de Brasília</span><a href="#methodology">Entenda os dados ↗</a></div>`;
}
function renderTables(){const html=tableHTML();$('records-table').innerHTML=html;$('full-table').innerHTML=html;$('table-summary').textContent=`${state.rows.length} registros no recorte selecionado · clique na via para ver os detalhes`;
 document.querySelectorAll('[data-record]').forEach(el=>el.addEventListener('click',()=>openDetail(el.dataset.record)));
 document.querySelectorAll('.export').forEach(el=>el.disabled=state.rows.length===0);
}
function renderTimeline(){
 const rows=state.rows.filter(r=>minutes(r.inicio_evento)!==null);
 if(!rows.length){$('timeline').innerHTML='<div class="empty">Nenhum intervalo disponível para os filtros selecionados.</div>';return;}
 // Calendar days have separate labelled rows. Overnight intervals extend beyond 24h.
 const intervals=rows.map(r=>({r,start:minutes(r.inicio_evento),length:duration(r)}));
 const min=Math.floor(Math.min(...intervals.map(i=>i.start))/30)*30;
 const max=Math.max(min+30,Math.ceil(Math.max(...intervals.map(i=>i.start+(i.length??0)))/30)*30);
 const label=n=>`${String(Math.floor(n/60)%24).padStart(2,'0')}:${String(n%60).padStart(2,'0')}${n>=1440?' +1d':''}`;
 $('timeline').innerHTML=`<div class="timeline-body"><div class="timeline-axis">${Array.from({length:5},(_,i)=>`<span>${label(Math.round(min+(max-min)*i/4))}</span>`).join('')}</div>${intervals.map(({r,start,length})=>`<button class="timeline-row" data-timeline="${escapeHTML(r.id)}" title="${escapeHTML(prettyStreet(r.logradouro))}: ${date(r.inicio_evento)}, ${time(r.inicio_evento)} a ${time(r.fim_evento)}"><span class="timeline-name">${escapeHTML(prettyStreet(r.logradouro))}<small>${shortDate(r.inicio_evento)}</small></span><span class="timeline-track"><span class="timeline-bar ${isBlocked(r)?'':'open'}" style="left:${100*(start-min)/(max-min)}%;width:${100*(length??0)/(max-min)}%"></span></span></button>`).join('')}<div class="timeline-note"><i class="legend-line"></i> Intransitável <span style="margin-left:14px"><i class="legend-line" style="background:#90ae8a"></i> Transitável</span> <span style="margin-left:14px">Cada linha representa um registro na data indicada; término ausente é mostrado como início.</span></div></div>`;
 document.querySelectorAll('[data-timeline]').forEach(el=>el.onclick=()=>openDetail(el.dataset.timeline));
}
function initMap(){
 if(!window.L){$('map-notice').innerHTML=`${icon('info')}<strong>O mapa não pôde carregar.</strong><p>Os registros seguem disponíveis na tabela. Atualize a página para tentar novamente.</p>`;return;}
 state.map=L.map('map',{scrollWheelZoom:false,zoomControl:true}).setView([-23.539,-46.452],13);
 let warned=false;
 const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'}).addTo(state.map);
 tiles.on('tileerror',()=>{if(!warned){warned=true;toast('Mapa base indisponível. Os dados locais continuam acessíveis.');}});
 state.eventLayer=L.geoJSON(null,{style:()=>({color:'#c97848',weight:5,opacity:.9}),pointToLayer:(f,p)=>L.circleMarker(p,{radius:7,color:'#c97848',fillOpacity:.8}),onEachFeature:(f,l)=>{const p=f.properties||{};const node=document.createElement('div');node.textContent=`${p.logradouro||'Ocorrência'} · ${fusionLabel(p.status_fusao)}`;l.bindPopup(node);l.on('click',()=>{if(p._id)openDetail(p._id);});}}).addTo(state.map);
 state.newsLayer=L.geoJSON(null,{style:()=>({color:'#418f85',weight:4,dashArray:'5 5'}),pointToLayer:(f,p)=>L.circleMarker(p,{radius:6,color:'#418f85'}),onEachFeature:(f,l)=>{const node=document.createElement('div');node.textContent=f.properties?.title||f.properties?.logradouro_extraido||'Notícia geolocalizada';l.bindPopup(node);}}).addTo(state.map);
 state.networkLayer=L.geoJSON(null,{style:()=>({color:'#667e64',weight:1,opacity:.35})});
 $('fit-map').onclick=fitMap;
 $('toggle-network').onclick=()=>{if(!state.data?.layers['itaquera_network.geojson']){toast('A malha viária ainda não está disponível no projeto.');return;}state.showNetwork=!state.showNetwork;$('toggle-network').setAttribute('aria-pressed',String(state.showNetwork));if(state.showNetwork)state.networkLayer.addTo(state.map);else state.map.removeLayer(state.networkLayer);};
}
function fitMap(){if(!state.map)return;const layers=[state.eventLayer,state.newsLayer].filter(Boolean);const bounds=L.featureGroup(layers).getBounds();if(bounds.isValid())state.map.fitBounds(bounds,{padding:[35,35],maxZoom:16});else state.map.setView([-23.539,-46.452],13);}
function renderMap(){
 if(!state.map)return;state.eventLayer.clearLayers();state.newsLayer.clearLayers();
 const fused=$('dataset').value==='fusion'?state.rows:[];
 const features=fused.filter(r=>r.geometry).map(r=>({type:'Feature',geometry:r.geometry,properties:{...r.original,_id:r.id}}));
 try{state.eventLayer.addData({type:'FeatureCollection',features});}catch{toast('Há uma geometria inválida no resultado da fusão.');}
 const news=state.data.layers['noticias_geolocalizadas.geojson'];
 const day=$('date').value,query=fold($('search').value),status=$('status').value;
 const newsFeatures=(news?.features||[]).filter(f=>!status&&(!day||dayKey(f.properties?.inicio_evento)===day)&&(!query||fold(`${f.properties?.title||''} ${f.properties?.logradouro_extraido||''}`).includes(query)));
 try{state.newsLayer.addData({type:'FeatureCollection',features:newsFeatures});}catch{toast('Há uma geometria inválida nas notícias geolocalizadas.');}
 const count=features.length+newsFeatures.length;$('map-count').textContent=`${count} geometria${count===1?'':'s'}`;
 $('map-notice').hidden=count>0;
 $('map-notice').innerHTML=`${icon('pin')}<strong>${state.data.fusion_available&&$('dataset').value==='cge'?'Explore o resultado da fusão':'Geometrias ainda não disponíveis'}</strong><p>${state.data.fusion_available&&$('dataset').value==='cge'?'Selecione “Resultado da fusão” no filtro de base para visualizar as vias processadas.':'Os registros deste recorte estão na tabela. As vias aparecerão aqui quando houver GeoJSONs correspondentes.'}</p><a href="#pipeline" style="display:inline-block;margin-top:10px;font-size:10px;color:#638b54">Ver etapas do processamento →</a>`;
}
function renderEvidence(){
 const d=state.data;
 $('evidence').innerHTML=[['database','Registros oficiais','CGE / SAISP · arquivo histórico',d.records.length],['document','Textos no corpus','Boletins e notícias coletados',d.articles.length],['layers','Ocorrências fusionadas',d.fusion_available?'GeoJSON disponível':'Aguardando processamento',d.fusion_available?d.fused.length:'—']].map(([i,t,s,n])=>`<div class="evidence-item"><span class="evidence-icon">${icon(i)}</span><div><strong>${t}</strong><small>${s}</small></div><b>${n}</b></div>`).join('');
}
function renderSources(){
 $('article-count').textContent=`${state.data.articles.length} textos únicos`;
 $('articles').innerHTML=state.data.articles.map(a=>{
  const r=a.raw,url=safeURL(r.source_url||r.url),title=r.title||r.titulo||'Texto sem título';
  const entities=Array.isArray(r.entities)?r.entities:Object.values(r.entities||{}).flat();
  const mentions=r.temporal_mentions||[],processed=a.files.some(f=>f.startsWith('processed/'));
  return `<article class="article-card"><div class="article-meta"><span class="pill ${processed?'green':'neutral'}">${processed?'Texto anotado':'Coleta bruta · não validada'}</span><span>${date(r.published_at||r.data_publicacao)}</span></div><h2>${escapeHTML(title)}</h2><div class="article-body">${escapeHTML(r.body||r.corpo_texto||'Texto não disponível.')}</div>${r.body_scope==='excerpt'?'<p class="muted">O arquivo contém um trecho do boletim original.</p>':''}<details ${processed?'open':''}><summary>Entidades identificadas (${entities.length})</summary>${entities.length?entities.map(e=>`<span class="entity">${escapeHTML(typeof e==='string'?e:e.text||e.entity)}${e.label?` · ${escapeHTML(e.label)}`:''}</span>`).join(''):'<p class="muted">Nenhuma anotação de entidade disponível.</p>'}</details><details><summary>Expressões temporais (${mentions.length})</summary>${mentions.map(m=>`<p class="muted"><strong>${escapeHTML(m.text)}</strong><br>${escapeHTML(m.start||m.value||'Sem início')} → ${escapeHTML(m.end||'Sem término')} · ${m.estimated?'estimado':'não estimado'}</p>`).join('')||'<p class="muted">Nenhuma anotação temporal disponível.</p>'}</details>${url?`<a class="source-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Ler na fonte original ${icon('external')}</a>`:''}<div class="article-files">${a.files.map(escapeHTML).join('<br>')}</div></article>`;
 }).join('')||'<div class="empty">Nenhum texto disponível na pasta data.</div>';
 $('files').innerHTML=state.data.files.map(f=>`<div class="file-row">${icon('document')}<div><strong>${escapeHTML(f.path)}</strong><small>${f.available?`${f.count} registros`:'Erro de leitura'} · ${(f.size/1024).toLocaleString('pt-BR',{maximumFractionDigits:1})} KB</small></div><a class="button secondary" href="/api/files/${f.path.split('/').map(encodeURIComponent).join('/')}" download>${icon('download')}Baixar</a></div>`).join('')||'<div class="empty">Nenhum arquivo de dados encontrado.</div>';
}
function renderPipeline(){
 const stages=[
 ['Ingestão de dados','Registros institucionais e notícias de origem.',['raw/noticias_itaquera.jsonl','raw/noticias_cge.jsonl','processed/cge_itaquera.csv'],'python -m src.cge.download'],
 ['Extração de entidades','Identificação de logradouros e pontos de referência.',['processed/noticias_anotadas.jsonl'],'python -m src.ner.annotate'],
 ['Normalização temporal','Expressões em português convertidas em intervalos de tempo.',['processed/noticias_temporais.jsonl'],'python -m src.temporal.normalize'],
 ['Geocodificação','Geometrias das notícias e malha viária do OpenStreetMap.',['processed/noticias_geolocalizadas.geojson','processed/itaquera_network.geojson'],'python -m src.spatial.geocode'],
 ['Fusão espaço-temporal','Cruzamento de proximidade espacial e sobreposição temporal.',['processed/intransitabilidade_itaquera_final.geojson'],'python -m src.spatial.fusion']];
 $('pipeline-stages').innerHTML=stages.map(([title,desc,files,command],i)=>{const present=files.filter(p=>state.data.files.some(f=>f.path===p&&f.available));const complete=present.length===files.length;return `<section class="pipeline-stage"><span class="stage-num">0${i+1}</span><div class="stage-main"><h3>${title}</h3><p>${desc}</p><details><summary>${present.length} de ${files.length} arquivos disponíveis · ver detalhes</summary><p style="margin-top:10px">${files.map(p=>`${present.includes(p)?'✓':'○'} ${p}`).join('<br>')}</p><code>${command}</code></details></div><span class="pill ${complete?'green':present.length?'blue':'neutral'}">${complete?'Disponível':present.length?'Parcial':'Pendente'}</span></section>`;}).join('');
 $('data-warnings').innerHTML=state.data.warnings.length?`<div class="error-banner">${state.data.warnings.map(escapeHTML).join('<br>')}</div>`:'';
}
function openDetail(id){
 const r=[...state.data.records,...state.data.fused].find(x=>x.id===id);if(!r)return;state.selected=id;
 const url=safeURL(r.source_url);const items=[['Início',`${date(r.inicio_evento)} · ${time(r.inicio_evento)}`],['Término',r.fim_evento?`${date(r.fim_evento)} · ${time(r.fim_evento)}`:'Não informado'],['Duração',duration(r)===null?'Em aberto':`${duration(r)} minutos`],['Sentido',r.sentido||'Não informado'],['Referência',r.referencia||'Não informada'],['Fontes declaradas',r.fontes||'Não informadas'],['Fusão',fusionLabel(r.status_fusao)],['Confiança heurística',typeof r.confianca_geral==='number'?r.confianca_geral.toLocaleString('pt-BR'):'Não atribuída']];
 $('detail-content').innerHTML=`<h2 id="detail-title" class="dialog-title">${escapeHTML(prettyStreet(r.logradouro))}</h2>${pill(r)}<dl class="detail-grid">${items.map(([k,v])=>`<div><dt>${k}</dt><dd>${escapeHTML(v)}</dd></div>`).join('')}</dl><p class="detail-note">${r.kind==='fusion'?'A confiança é uma regra do pipeline, não uma probabilidade calibrada. A etiqueta de fonte reproduz o arquivo gerado; o corpus anotado atual é um boletim CGE, não uma reportagem independente.':'Registro institucional preservado do CSV de origem. Sem geometria associada ou confiança atribuída antes da fusão.'}</p>${url?`<a class="button secondary" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Abrir boletim original ${icon('external')}</a>`:''}<details><summary>Ver dados originais</summary><pre class="raw-data">${escapeHTML(JSON.stringify(r.original,null,2))}</pre></details>`;
 if(!$('detail').open)$('detail').showModal();
}
function exportCSV(){
 const fields=['logradouro','inicio_evento','fim_evento','status_via','status_fusao','fontes','confianca_geral','referencia','sentido','source_url'];
 const cell=value=>{let v=String(value??'');if(/^[\s]*[=+@-]/.test(v))v="'"+v;return `"${v.replace(/"/g,'""')}"`;};
 const content='\uFEFF'+[fields.join(';'),...state.rows.map(r=>fields.map(f=>cell(r[f])).join(';'))].join('\r\n');
 const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`flood-fusion-${$('dataset').value}-${$('date').value||'periodo-completo'}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`${state.rows.length} registros exportados.`);
}
async function load(){
 const button=$('refresh');button.disabled=true;$('load-error').hidden=true;
 try{
  const response=await fetch('/api/dashboard',{signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Não foi possível ler os dados.');
  state.data=await response.json();$('loading').hidden=true;$('app').hidden=false;
  $('nav-count').textContent=state.data.records.length;
  updateDates();renderEvidence();renderSources();renderPipeline();filterRows();
  if(state.map){state.networkLayer.clearLayers();const network=state.data.layers['itaquera_network.geojson'];if(network)try{state.networkLayer.addData(network);}catch{toast('Não foi possível desenhar a malha viária.');}state.map.invalidateSize();}
  $('loaded-at').textContent=`Leitura local às ${time(state.data.loaded_at)} · ${date(state.data.loaded_at)}`;
  if(state.data.warnings.length){$('load-error').textContent='Alguns arquivos não puderam ser lidos. Consulte os detalhes em Pipeline de dados.';$('load-error').hidden=false;}
  navigate();
 }catch(error){$('loading').hidden=true;$('load-error').textContent=`Não foi possível atualizar os dados. Verifique se o servidor Python está rodando e clique em Atualizar dados.${state.data?' Os dados da última leitura foram mantidos.':''}`;$('load-error').hidden=false;}
 finally{button.disabled=false;}
}
$('refresh').onclick=load;
$('search').addEventListener('input',filterRows);
['date','status'].forEach(id=>$(id).addEventListener('change',filterRows));
$('dataset').onchange=()=>{updateDates();filterRows();fitMap();};
$('clear').onclick=()=>{$('search').value='';$('date').value='';$('status').value='';filterRows();};
document.querySelectorAll('.export').forEach(el=>el.onclick=exportCSV);
$('close-detail').onclick=()=>$('detail').close();
$('detail').addEventListener('click',e=>{if(e.target===$('detail')){const r=$('detail').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('detail').close();}});
window.addEventListener('hashchange',navigate);
navigate();initMap();load();
