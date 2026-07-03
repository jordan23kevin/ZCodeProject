/* check_rem.js — AI 去背 贴图 OS v2.1.5 (前端交互) */
function showToast(m){var t=document.getElementById('toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',3500);}
function toggleSelectAll(checked){
  document.querySelectorAll('.card').forEach(function(card){
    if(card.style.display!=='none'){
      var cb=card.querySelector('.dx-check');
      if(cb) cb.checked=checked;
    }
  });
  updateBatchBtn();
}
function updateBatchBtn(){
  var n=0;
  document.querySelectorAll('.card').forEach(function(card){
    if(card.style.display!=='none'){
      var cb=card.querySelector('.dx-check');
      if(cb&&cb.checked) n++;
    }
  });
  var btn=document.getElementById('batchBtn');
  btn.disabled=n===0;
  btn.textContent='⚡ 批量去背 ('+n+')';
  var sbtn=document.getElementById('batchStickerBtn');
  if(sbtn){sbtn.disabled=n===0; sbtn.textContent='📎 批量贴图 ('+n+')';}
  var ibtn=document.getElementById('batchInvertBtn');
  if(ibtn){ibtn.disabled=n===0; ibtn.textContent='🌑 批量反相 ('+n+')';}
}
function batchRembg(){
  var checked=document.querySelectorAll('.dx-check:checked');
  if(!checked.length){showToast('请先勾选需要去背的款');return;}
  if(!confirm('批量去背 '+checked.length+' 个款？一次美图处理全部。'))return;
  var dxList=[];
  checked.forEach(function(cb){dxList.push(cb.getAttribute('data-dx'));});
  var btn=document.getElementById('batchBtn');
  btn.disabled=true;btn.textContent='⏳ 启动中…';
  showToast('⏳ 启动批量去背，共 '+dxList.length+' 款…');
  fetch('/batch-rembg?dx='+dxList.join(',')).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){showToast('❌ '+d.msg);btn.textContent='⚡ 批量去背 (0)';return;}
    showToast(d.msg);
    var pollTimer=setInterval(function(){
      fetch('/batch-result').then(function(r){return r.json();}).then(function(res){
        if(!res.done){showToast(res.msg);return;}
        clearInterval(pollTimer);
        var okN=0,failN=0;
        if(res.results){
          for(var i=0;i<res.results.length;i++){
            if(res.results[i].ok) okN++; else failN++;
          }
        }
        btn.textContent='⚡ 批量去背 (0)';
        btn.disabled=false;
        if(failN){
          showToast('✅ 完成 '+okN+'/'+res.results.length+'，'+failN+' 个失败，刷新页面查看');
        }else{
          showToast('✅ 批量去背完成！共 '+res.results.length+' 张');
        }
        setTimeout(function(){location.reload();},3000);
      });
    },2000);
  });
}
function openFolder(dx,which){
  var x=new XMLHttpRequest();
  x.open('GET','/open?dx='+dx+'&which='+which,true);
  x.send();
}
function copyDx(dx){navigator.clipboard.writeText(dx).then(()=>{showToast('已复制 '+dx);}).catch(()=>{showToast('复制失败，请手动复制');});}
function copyMissing(){
  var cards=document.querySelectorAll('.card');
  var miss=[];
  cards.forEach(function(c){
    if(c.innerHTML.indexOf('⚠ 缺')>=0) miss.push(c.getAttribute('data-dx'));
  });
  if(!miss.length){showToast('当前页面没有缺图款'); return;}
  navigator.clipboard.writeText(miss.join(',')).then(()=>{showToast('已复制 '+miss.length+' 个缺图款: '+miss.join(','));}).catch(()=>{showToast('复制失败');});
}
function renameStem(dx,stem){
  var msg='将 '+dx+'/'+stem+' 改为BW？\n文件: '+stem+'.png → '+stem.slice(0,-2)+'_BW.png\n去背: '+stem+'_cut.png → '+stem.slice(0,-2)+'_BW_cut.png';
  if(!confirm(msg))return;
  fetch('/rename?dx='+dx+'&stem='+encodeURIComponent(stem)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok) setTimeout(function(){ location.reload(); },1500);});
}
function delImg(dx,which,file,cellId){
  if(!confirm('删除 '+dx+'/'+which+'/'+file+' ？（送回收站，可撤销）'))return;
  fetch('/del?dx='+dx+'&which='+which+'&file='+encodeURIComponent(file)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok)document.getElementById(cellId).classList.add('deleted');});
}
function rembg(dx,file){
  var msg='重新去背 '+dx+'/'+file+' ？\n将启动美图秀秀自动操作（接管屏幕），期间请勿动键鼠。\n旧去背图会先备份，失败可自动还原。';
  if(!confirm(msg))return;
  showToast('⏳ 正在启动美图秀秀…请勿动键鼠');
  fetch('/rembg?dx='+dx+'&file='+encodeURIComponent(file)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok)setTimeout(()=>location.reload(),4000);});
}
function switchDate(d){window.location.href = d ? '/'+d+'/' : '/';}
function psSticker(dx){
  if(!confirm('启动 PS贴图（含BW合成） '+dx+' ？\nPS将打开，请勿动键鼠。'))return;
  showToast('⏳ 启动PS贴图（含BW合成） '+dx+'…');
  fetch('/ps-sticker?dx='+dx).then(function(r){return r.json();}).then(function(d){showToast(d.msg);if(d.ok)setTimeout(function(){location.reload();},3000);});
}
function psBatch(dx){
  if(!confirm('启动 BW合成 '+dx+' ？\n将合成白BW/黑BW。'))return;
  showToast('⏳ BW合成 '+dx+'…');
  fetch('/ps-batch?dx='+dx).then(function(r){return r.json();}).then(function(d){showToast(d.msg);if(d.ok)setTimeout(function(){location.reload();},3000);});
}
function batchSticker(){
  var checked=document.querySelectorAll('.dx-check:checked');
  if(!checked.length){showToast('请先勾选需要贴图的款');return;}
  if(!confirm('批量贴图（含BW合成） '+checked.length+' 个款？\n请确保PS未在使用中。'))return;
  var list=[];
  checked.forEach(function(cb){list.push(cb.getAttribute('data-dx'));});
  var btn=document.getElementById('batchStickerBtn');
  btn.disabled=true;btn.textContent='⏳ 启动中…';
  showToast('⏳ 启动批量贴图（含BW合成） '+list.length+' 款…');
  // 逐个启动（PS单任务处理）
  var i=0;
  function runNext(){
    if(i>=list.length){
      btn.textContent='📎 批量贴图 (0)';btn.disabled=false;
      showToast('✅ 批量贴图（含BW合成）已全部启动，3秒后刷新');
      setTimeout(function(){location.reload();},3000);
      return;
    }
    fetch('/ps-sticker?dx='+list[i]).then(function(r){return r.json();}).then(function(d){
      showToast('📎 ('+(i+1)+'/'+list.length+') '+list[i]+': '+d.msg);
      i++;
      if(i<list.length) setTimeout(runNext,2000); else runNext();
    });
  }
  runNext();
}
function batchInvertRem(){
  var checked=document.querySelectorAll('.dx-check:checked');
  if(!checked.length){showToast('请先勾选需要批量反相的款');return;}
  if(!confirm('批量反相 '+checked.length+' 个款？\n将对每款的 B/W/BW 去背图生成黑版专用图，并自动完成贴图+BW合成。'))return;
  var list=[];
  checked.forEach(function(cb){list.push(cb.getAttribute('data-dx'));});
  var btn=document.getElementById('batchInvertBtn');
  btn.disabled=true;btn.textContent='⏳ 启动中…';
  showToast('⏳ 启动批量反相（含贴图+BW合成） '+list.length+' 款…');
  fetch('/batch-invert-rem?dx='+list.join(',')).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){showToast('❌ '+d.msg);btn.textContent='🌑 批量反相 (0)';btn.disabled=false;return;}
    showToast(d.msg);
    var pollTimer=setInterval(function(){
      fetch('/batch-invert-result').then(function(r){return r.json();}).then(function(res){
        if(!res.done){showToast(res.msg);return;}
        clearInterval(pollTimer);
        var okN=0,failN=0;
        if(res.results){
          for(var i=0;i<res.results.length;i++){
            if(res.results[i].ok) okN++; else failN++;
          }
        }
        btn.textContent='🌑 批量反相 (0)';
        btn.disabled=false;
        if(failN){
          showToast('✅ 完成 '+okN+'/'+res.results.length+'，'+failN+' 个失败，刷新页面查看');
        }else{
          showToast('✅ 批量反相完成！共 '+res.results.length+' 款');
        }
        setTimeout(function(){location.reload();},3000);
      });
    },2000);
  });
}
function copyNoSticker(){
  var cards=document.querySelectorAll('.card');
  var nos=[];
  cards.forEach(function(c){
    if(c.style.display==='none') return;
    var bar=c.querySelector('.upload-bar');
    if(!bar || bar.innerHTML.indexOf('未贴图')>=0) nos.push(c.getAttribute('data-dx'));
  });
  if(!nos.length){showToast('当前页面所有款都已贴图'); return;}
  navigator.clipboard.writeText(nos.join(',')).then(function(){showToast('已复制 '+nos.length+' 个缺贴图款');}).catch(function(){showToast('复制失败');});
}
function upscaleRem(dx,file,cellId){
  if(!confirm('放大 '+file+' 到2046x2046？'))return;
  showToast('⏳ 放大中…');
  fetch('/upscale-rem?dx='+dx+'&file='+encodeURIComponent(file)).then(function(r){return r.json();}).then(function(d){
    showToast(d.msg);
    if(d.ok){
      // 刷新缩略图
      var img=document.querySelector('#img-'+cellId);
      if(img) img.src=img.src.split('&t=')[0]+'&t='+Date.now();
    }
  });
}
function invertRem(dx,file,stem,cellId){
  if(!confirm('反相 '+file+' 生成黑版贴图？\n将生成 '+dx+'_黑'+stem.replace(dx+'_','')+'_cut.png，并自动重跑该款全部贴图+BW合成。'))return;
  showToast('⏳ 反相并重新贴图/BW合成…');
  fetch('/invert-rem?dx='+dx+'&file='+encodeURIComponent(file)).then(function(r){return r.json();}).then(function(d){
    showToast(d.msg);
    if(d.ok) setTimeout(function(){location.reload();},3000);
  });
}
function refreshRem(dx,stem,cellId){
  showToast('🔄 刷新 '+stem+' 去背预览…');
  fetch('/refresh-thumb?dx='+dx+'&stem='+encodeURIComponent(stem)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok && d.found && d.url){
    var cell=document.getElementById(cellId);if(!cell) return;
    var wrap=cell.parentNode; if(!wrap || wrap.className.indexOf('cell-wrap')<0) return;
    var showUp=(d.w<2000 || d.h<2000);
    var dimText=(d.w&&d.h)?(d.w+'x'+d.h):'';
    var upBtn=showUp?'<button class="upscale" onclick="upscaleRem(&quot;'+dx+'&quot;,&quot;'+d.file+'&quot;,&quot;'+cellId+'&quot;)" title="放大到2046x2046">🔍</button>':'';
    var dimHint=showUp?'<span class="dim-hint" title="当前分辨率">'+dimText+'</span>':'';
    var invBtn=(d.file.indexOf('_黑')<0)?'<button class="invert" onclick="invertRem(&quot;'+dx+'&quot;,&quot;'+d.file+'&quot;,&quot;'+stem+'&quot;,&quot;'+cellId+'&quot;)" title="生成黑版反相贴图">反相</button>':'';
    wrap.innerHTML='<div class="cell" id="'+cellId+'">'
      +'<img id="img-'+cellId+'" src="'+d.url+'" onclick="openFolder(&quot;'+dx+'&quot;,&quot;rem&quot;)">'
      +'<span class="tag">REM</span></div>'
      +'<div class="btn-bar">'
      +'<button class="del" onclick="delImg(&quot;'+dx+'&quot;,&quot;rem&quot;,&quot;'+d.file+'&quot;,&quot;'+cellId+'&quot;)" title="删除去背图">×</button>'
      +'<button class="refr" onclick="refreshRem(&quot;'+dx+'&quot;,&quot;'+stem+'&quot;,&quot;'+cellId+'&quot;)" title="刷新这张去背图预览">🔄</button>'
      +invBtn
      +upBtn+dimHint
      +'<span class="btn-stem">'+stem+'</span>'
      +'</div>';
    bindPreview(wrap.querySelector('.cell'));
  }});
}
function filterCards(){
  var q=document.getElementById('search').value.toUpperCase().trim();
  var cards=document.querySelectorAll('.card');
  var n=0;
  var terms = q ? q.split(',').map(function(t){ return t.trim(); }).filter(function(t){ return t; }) : [];
  cards.forEach(function(c){
    var dx=c.getAttribute('data-dx').toUpperCase();
    var show = false;
    if (!terms.length) { show = true; }
    else { for (var i=0;i<terms.length;i++) { if (dx.indexOf(terms[i])>=0) { show=true; break; } } }
    c.style.display=show?'':'none';
    if(show) n++;
  });
  document.getElementById('cnt').textContent=n+' 款';
}
// 悬停预览：等图片加载后用实际尺寸定位，避免乱跳
var prevEl=document.getElementById('preview');
var prevImg=document.getElementById('previewImg');
function bindPreview(cell){
  if(!cell) return;
  cell.addEventListener('mouseenter',function(){
    var img=this.querySelector('img'); if(!img)return;
    var src=img.getAttribute('data-src')||img.src;
    prevImg.src=src.replace('/thumb?','/original?');
    prevEl.style.display='block';
    prevEl.style.visibility='hidden';
    prevEl.style.left='0px'; prevEl.style.top='0px';
    var self=this;
    function positionPreview(){
      var r=self.getBoundingClientRect();
      var pw=prevEl.offsetWidth||900, ph=prevEl.offsetHeight||Math.floor(window.innerHeight*0.9);
      var margin=8;
      // 默认放 cell 右侧，顶部对齐
      var left=r.right+margin, top=r.top;
      // 右边放不下就放左边
      if(left+pw>window.innerWidth-margin) left=r.left-pw-margin;
      // 左边仍放不下则贴左边缘
      if(left<margin) left=margin;
      // 下方放不下则向上平移，只移必要距离
      if(top+ph>window.innerHeight-margin) top=window.innerHeight-ph-margin;
      // 上方仍放不下则贴顶部
      if(top<margin) top=margin;
      prevEl.style.left=left+'px'; prevEl.style.top=top+'px';
      prevEl.style.visibility='visible';
    }
    if(prevImg.complete && prevImg.naturalWidth>0){
      positionPreview();
    } else {
      prevImg.onload=positionPreview;
      // 缓存命中也可能不触发 load，兜底 100ms 后定位
      setTimeout(positionPreview, 100);
    }
  });
  cell.addEventListener('mouseleave',function(){prevEl.style.display='none'; prevImg.onload=null;});
}
document.querySelectorAll('.cell').forEach(bindPreview);

// UID / group_id 分组：把黑版变体行移动到同 group_id 的 AI/REM pair 下方
function groupBlackVariants(){
  document.querySelectorAll('.black-variant-row').forEach(function(bv){
    var gid=bv.getAttribute('data-group-id');
    if(!gid) return;
    var target=null;
    // 优先匹配普通 pair
    document.querySelectorAll('.pair[data-group-id]').forEach(function(pair){
      if(pair.getAttribute('data-group-id')===gid && pair.getAttribute('data-kind')!=='black-variant'){
        target=pair;
      }
    });
    // 再匹配 B/W 配对行
    if(!target){
      document.querySelectorAll('.bw-group').forEach(function(g){
        if(g.getAttribute('data-group-left')===gid || g.getAttribute('data-group-right')===gid){
          target=g;
        }
      });
    }
    if(target && target.nextSibling!==bv){
      target.parentNode.insertBefore(bv, target.nextSibling);
      var stem=bv.querySelector('.stem');
      if(stem) stem.style.display='none';
      bv.style.borderTop='none';
    }
  });
}

// 后端项目数据缓存（供按 stem 查找 group_id/uid 的 fallback 使用）
var _projectsCache=null;
function fetchProjects(){
  if(_projectsCache) return Promise.resolve(_projectsCache);
  return fetch('/api/projects').then(function(r){return r.json();}).then(function(d){
    _projectsCache=d; return d;
  }).catch(function(){ return []; });
}
function resolveGroupIdByStem(dx, stem){
  // 优先 DOM
  var el=document.querySelector('.pair[data-stem="'+stem+'"], .bw-half[data-stem="'+stem+'"], .black-variant[data-stem="'+stem+'"]');
  if(el) return Promise.resolve(el.getAttribute('data-group-id'));
  // fallback 到 /api/projects
  return fetchProjects().then(function(projects){
    for(var i=0;i<projects.length;i++){
      if(projects[i].dx!==dx) continue;
      var pairs=projects[i].pairs||[];
      for(var j=0;j<pairs.length;j++){
        if(pairs[j].stem===stem) return pairs[j].group_id;
      }
      var bvs=projects[i].black_variants||[];
      for(var j=0;j<bvs.length;j++){
        if(bvs[j].stem===stem) return bvs[j].group_id;
      }
    }
    return null;
  });
}
document.addEventListener('DOMContentLoaded', groupBlackVariants);