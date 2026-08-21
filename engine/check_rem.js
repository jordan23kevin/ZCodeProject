/* check_rem.js — AI 去背 贴图 OS v2.7.2 (前端交互) */
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
  if(ibtn){ibtn.disabled=n===0; ibtn.textContent='🌑 批量反黑 ('+n+')';}
  var iwbtn=document.getElementById('batchInvertWhiteBtn');
  if(iwbtn){iwbtn.disabled=n===0; iwbtn.textContent='☀ 批量反白 ('+n+')';}
}
function batchRembg(){
  var checked=document.querySelectorAll('.dx-check:checked');
  if(!checked.length){showToast('请先勾选需要去背的款');return;}
  if(!confirm('批量去背 '+checked.length+' 个款？一次美图处理全部。\n若已有去背任务正在运行，将被强制中断。'))return;
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
function renameStemOptions(dx,stem,btn){
  // 用传进来的 dx 去掉前缀，能正确处理带 BW/B/W 后缀的款号（如 DX0694BW_B）
  var suffix = (stem.indexOf(dx + '_') === 0) ? stem.slice(dx.length + 1) : stem.replace(/^DX\d+_/, '');
  // 区分黑版前缀、基础 role、版本号：黑B5 -> 黑 + B + 5
  var isBlack = suffix.indexOf('黑') === 0;
  var rolePart = isBlack ? suffix.slice(1) : suffix;          // B5
  var baseRole = rolePart.replace(/\d+$/, '');                 // B
  var version = rolePart.replace(/^\D+/, '');                  // 5
  var blackPrefix = isBlack ? '黑' : '';
  var targets = [];
  if(baseRole === 'B') targets = [blackPrefix+'W'+version, blackPrefix+'BW'+version];
  else if(baseRole === 'W') targets = [blackPrefix+'B'+version, blackPrefix+'BW'+version];
  else if(baseRole === 'BW' || baseRole === 'WB') targets = [blackPrefix+'B'+version, blackPrefix+'W'+version];
  else targets = [blackPrefix+'B'+version, blackPrefix+'W'+version, blackPrefix+'BW'+version];

  var old = document.getElementById('ren-menu');
  if(old) old.remove();

  var menu = document.createElement('div');
  menu.id = 'ren-menu';
  menu.style.cssText = 'position:absolute;z-index:100;background:#333;border:1px solid #555;border-radius:4px;padding:4px;display:flex;gap:4px;box-shadow:0 2px 8px rgba(0,0,0,.5);';
  targets.forEach(function(t){
    var b = document.createElement('button');
    b.textContent = t;
    b.style.cssText = 'background:#4caf50;color:#fff;border:none;border-radius:3px;padding:2px 8px;cursor:pointer;font-size:12px;';
    b.onmouseover = function(){ this.style.background='#388e3c'; };
    b.onmouseout = function(){ this.style.background='#4caf50'; };
    b.onclick = function(e){
      e.stopPropagation();
      menu.remove();
      fetch('/rename?dx='+dx+'&stem='+encodeURIComponent(stem)+'&target='+encodeURIComponent(t)).then(function(r){return r.json();}).then(function(d){
        showToast(d.msg);
        if(d.ok) setTimeout(function(){ location.reload(); }, 800);
      });
    };
    menu.appendChild(b);
  });
  document.body.appendChild(menu);
  var r = btn.getBoundingClientRect();
  menu.style.left = (r.left + window.scrollX) + 'px';
  menu.style.top = (r.bottom + window.scrollY + 2) + 'px';

  function close(e){ if(!menu.contains(e.target)){ menu.remove(); document.removeEventListener('click', close); } }
  setTimeout(function(){ document.addEventListener('click', close); }, 0);
}
function delImg(dx,which,file,cellId){
  if(!confirm('删除 '+dx+'/'+which+'/'+file+' ？（送回收站，可撤销）'))return;
  fetch('/del?dx='+dx+'&which='+which+'&file='+encodeURIComponent(file)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok)document.getElementById(cellId).classList.add('deleted');});
}
function resticker(dx,file,cellId){
  if(!confirm('重新贴图 '+dx+'/'+file+' ？\n仅重新生成这一张，不影响同款其他贴图。'))return;
  showToast('⏳ 正在重新贴图 '+file+'…');
  fetch('/resticker?dx='+dx+'&file='+encodeURIComponent(file)).then(r=>r.json()).then(d=>{
    showToast(d.msg);
    if(d.ok){
      var item=document.getElementById(cellId);
      if(item){
        var img=item.querySelector('img');
        if(img) img.src=img.src.split('&t=')[0]+'&t='+Date.now();
      }
    }
  }).catch(function(e){
    showToast('❌ 重新贴图请求失败：'+e);
  });
}
function rembg(dx,file){
  var msg='重新去背 '+dx+'/'+file+' ？\n将启动美图秀秀自动操作（接管屏幕），期间请勿动键鼠。\n若已有去背任务正在运行，将被强制中断。\n旧去背图会先备份，失败可自动还原。';
  if(!confirm(msg))return;
  showToast('⏳ 正在启动美图秀秀…请勿动键鼠');
  fetch('/rembg?dx='+dx+'&file='+encodeURIComponent(file)).then(r=>r.json()).then(d=>{showToast(d.msg);if(d.ok)setTimeout(()=>location.reload(),4000);});
}
function switchDate(d){window.location.href = d ? '/'+d+'/' : '/';}
function psSticker(dx){
  if(!confirm('启动 PS贴图（含BW合成） '+dx+' ？\nPS将打开，做完该款后关闭，请勿动键鼠。'))return;
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
  if(!confirm('批量贴图（含BW合成） '+checked.length+' 个款？\n本次只贴白T+合成BW，不会反相/处理黑版文件。Photoshop 将全程保持开启，全部做完后再关闭。'))return;
  var list=[];
  checked.forEach(function(cb){list.push(cb.getAttribute('data-dx'));});
  var btn=document.getElementById('batchStickerBtn');
  btn.disabled=true;btn.textContent='⏳ 贴图中…';
  showToast('⏳ 批量贴图（含BW合成） '+list.length+' 款，PS 全程开启…');
  fetch('/ps-sticker?dx='+list.join(',')).then(function(r){return r.json();}).then(function(d){
    btn.textContent='📎 批量贴图 (0)';btn.disabled=false;
    showToast((d.ok?'✅':'⚠️')+' 批量贴图完成：'+d.msg);
    setTimeout(function(){location.reload();},3000);
  }).catch(function(e){
    btn.textContent='📎 批量贴图 (0)';btn.disabled=false;
    showToast('❌ 批量贴图请求失败：'+e);
  });
}
function batchInvertRem(mode){
  var checked=document.querySelectorAll('.dx-check:checked');
  if(!checked.length){showToast('请先勾选需要批量反相的款');return;}
  var label=mode=='black'?'反黑':'反白';
  var prefix=mode=='black'?'黑版':'白版';
  if(!confirm('批量'+label+' '+checked.length+' 个款？\n将对每款的 B/W/BW 去背图生成'+prefix+'专用图，并自动完成贴图+BW合成。'))return;
  var list=[];
  checked.forEach(function(cb){list.push(cb.getAttribute('data-dx'));});
  var btnId=mode=='black'?'batchInvertBtn':'batchInvertWhiteBtn';
  var btn=document.getElementById(btnId);
  var defaultText=mode=='black'?'🌑 批量反黑 (0)':'☀ 批量反白 (0)';
  btn.disabled=true;btn.textContent='⏳ 启动中…';
  showToast('⏳ 启动批量'+label+'（含贴图+BW合成） '+list.length+' 款…');
  fetch('/batch-invert-rem?dx='+list.join(',')+'&mode='+mode).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){showToast('❌ '+d.msg);btn.textContent=defaultText;btn.disabled=false;return;}
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
        btn.textContent=defaultText;
        btn.disabled=false;
        if(failN){
          showToast('✅ 完成 '+okN+'/'+res.results.length+'，'+failN+' 个失败，刷新页面查看');
        }else{
          showToast('✅ 批量'+label+'完成！共 '+res.results.length+' 款');
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
function invertRem(dx,file,stem,cellId,mode){
  var prefix = mode=='black' ? '黑' : '白';
  var title = mode=='black' ? '黑版白色剪影贴图' : '白版黑色剪影贴图';
  if(!confirm('反相 '+file+' 生成'+title+'？\n将生成 '+dx+'_'+prefix+stem.replace(dx+'_','')+'_cut.png，并自动重跑该款全部贴图+BW合成。'))return;
  showToast('⏳ 已加入队列，等待后台处理…');
  fetch('/invert-rem?dx='+dx+'&file='+encodeURIComponent(file)+'&mode='+mode).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){showToast('❌ '+d.msg);return;}
    showToast(d.msg);
    var pollTimer=setInterval(function(){
      fetch('/invert-queue-status').then(function(r){return r.json();}).then(function(res){
        if(res.queue_len===0 && !res.running && res.last_result){
          clearInterval(pollTimer);
          showToast((res.last_result.ok?'✅':'⚠️')+' '+res.last_result.msg);
          setTimeout(function(){location.reload();},3000);
        }
      });
    },2000);
  }).catch(function(e){showToast('❌ 请求失败：'+e);});
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
    var isSpecial=(d.file.indexOf('_黑')>=0 || d.file.indexOf('_白')>=0);
    var invBtn=isSpecial?'':(
      '<button class="invert black" onclick="invertRem(&quot;'+dx+'&quot;,&quot;'+d.file+'&quot;,&quot;'+stem+'&quot;,&quot;'+cellId+'&quot;,&quot;black&quot;)" title="生成黑版白色剪影贴图">反黑</button>'
      +'<button class="invert white" onclick="invertRem(&quot;'+dx+'&quot;,&quot;'+d.file+'&quot;,&quot;'+stem+'&quot;,&quot;'+cellId+'&quot;,&quot;white&quot;)" title="生成白版黑色剪影贴图">反白</button>'
    );
    wrap.innerHTML='<div class="cell" id="'+cellId+'">'
      +'<img id="img-'+cellId+'" src="'+d.url+'" onclick="openFolder(&quot;'+dx+'&quot;,&quot;rem&quot;)">'
      +'<span class="tag">REM</span></div>'
      +'<div class="btn-bar">'
      +'<button class="del" onclick="delImg(&quot;'+dx+'&quot;,&quot;rem&quot;,&quot;'+d.file+'&quot;,&quot;'+cellId+'&quot;)" title="删除去背图">×</button>'
      +'<button class="refr" onclick="refreshRem(&quot;'+dx+'&quot;,&quot;'+stem+'&quot;,&quot;'+cellId+'&quot;)" title="刷新这张去背图预览">↻</button>'
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
// 轮询 PS / 后台任务状态并更新页面摘要
function pollPsStatus(){
  var el=document.getElementById('psStatus');
  var txt=document.getElementById('psStatusText');
  var barWrap=document.getElementById('psBarWrap');
  var bar=document.getElementById('psBar');
  if(!el||!txt) return;
  fetch('/ps-status').then(function(r){return r.json();}).then(function(d){
    if(d.running){
      // 解析进度 X/Y（如 "12/90"）→ 显示「进度 12/90 款（还剩 78 款）」
      var done=0, total=0, hasFrac=false;
      if(d.progress && /^(\d+)\/(\d+)$/.test(d.progress.trim())){
        var m=d.progress.trim().match(/^(\d+)\/(\d+)$/);
        done=parseInt(m[1],10); total=parseInt(m[2],10); hasFrac=true;
      }
      var msg=d.task||'PS 运行中';
      if(d.current_dx) msg += ' · 正在处理 ' + d.current_dx;
      if(hasFrac){
        var remain=Math.max(total-done,0);
        msg += ' · 进度 ' + done + '/' + total + ' 款（还剩 ' + remain + ' 款）';
      } else if(d.progress){
        msg += ' · ' + d.progress;
      }
      if(d.detail && d.detail!==msg && d.detail.indexOf('正在处理')<0 && d.detail.indexOf('进度')<0){
        msg += ' · ' + d.detail;
      }
      txt.textContent=msg;
      if(barWrap && bar){
        if(hasFrac && total>0){
          bar.style.width=(done/total*100).toFixed(1)+'%';
          barWrap.style.display='inline-block';
        } else {
          bar.style.width='100%';
          barWrap.style.display='none';
        }
      }
      el.classList.add('show');
    }else{
      txt.textContent='PS 空闲';
      if(barWrap) barWrap.style.display='none';
      if(bar) bar.style.width='0%';
      el.classList.remove('show');
    }
  }).catch(function(){
    txt.textContent='PS 空闲';
    el.classList.remove('show');
  });
}

document.addEventListener('DOMContentLoaded', function(){
  groupBlackVariants();

  // 启动 PS 状态轮询（每 0.8 秒一次，快照更密、数字跳动更小）
  pollPsStatus();
  setInterval(pollPsStatus, 800);

  // 回到顶部按钮
  var topBtn=document.getElementById('backToTop');
  function toggleTopBtn(){
    if(!topBtn) return;
    if(window.scrollY>200){ topBtn.classList.add('show'); }
    else { topBtn.classList.remove('show'); }
  }
  window.addEventListener('scroll', toggleTopBtn, {passive:true});
  toggleTopBtn();

  // 滚动/缩放/Esc 时关闭改名选项菜单
  function closeRenameMenu(){
    var m=document.getElementById('ren-menu');
    if(m) m.remove();
  }
  window.addEventListener('scroll', closeRenameMenu, {passive:true});
  window.addEventListener('resize', closeRenameMenu);
  document.addEventListener('keydown', function(e){
    if(e.key==='Escape'){
      closeRenameMenu();
      // Esc 也清空搜索框
      var s=document.getElementById('search');
      if(s && document.activeElement!==s){ s.value=''; filterCards(); }
    }
    // / 键聚焦搜索框（不在输入框时）
    if(e.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){
      e.preventDefault();
      var s=document.getElementById('search');
      if(s){ s.focus(); s.select(); }
    }
  });
});

/* ---- v2.7.1 成品审图：总览网格（同色同列）+ 单图模式 ---- */
var revState={dx:null,idx:0,view:'grid'};
function revFiles(){
  return (UP_FILES[revState.dx]||[]).filter(function(f){return !f._deleted;});
}
function revColors(){
  var out=[],seen={};
  revFiles().forEach(function(f){
    var c=f.c||'其他';
    if(!seen[c]){seen[c]={c:c,items:[]};out.push(seen[c]);}
    seen[c].items.push(f);
  });
  return out;
}
function openRev(dx,fIdx){
  var all=UP_FILES[dx]||[];
  var list=all.filter(function(f){return !f._deleted;});
  if(!list.length){showToast('该款没有可审阅的成品图');return;}
  revState.dx=dx;
  revState.view='grid';
  revState.idx=(fIdx>0&&all[fIdx]&&!all[fIdx]._deleted)?list.indexOf(all[fIdx]):0;
  if(revState.idx<0)revState.idx=0;
  renderRev();
  document.getElementById('rev').classList.add('active');
}
function closeRev(){
  revState.dx=null;
  document.getElementById('rev').classList.remove('active');
  document.getElementById('revStage').innerHTML='';
}
function revToGrid(){revState.view='grid';renderRev();}
// 跨款移动：返回下/上一个有成品图的款，到尽头返回 null
function revJump(d){
  var pos=DX_ORDER.indexOf(revState.dx);
  if(pos<0)return null;
  var i=pos+d;
  while(i>=0&&i<DX_ORDER.length){
    var dx=DX_ORDER[i];
    if((UP_FILES[dx]||[]).some(function(f){return !f._deleted;}))return dx;
    i+=d;
  }
  return null;
}
function revStep(d){
  var list=revFiles();
  if(!list.length)return;
  var ni=revState.idx+d;
  if(ni>=0&&ni<list.length){revState.idx=ni;renderRev();return;}
  var nd=revJump(d);
  if(!nd){showToast(d>0?'已经是最后一款的最后一张':'已经是第一款的第一张');return;}
  revState.dx=nd;
  revState.idx=d>0?0:revFiles().length-1;
  renderRev();
}
// 总览模式 ←/→：整款切换（保持总览）
function revJumpGrid(d){
  var nd=revJump(d);
  if(!nd){showToast(d>0?'已经是最后一款':'已经是第一款');return;}
  revState.dx=nd;revState.idx=0;
  renderRev();
}
function revGo(i){revState.idx=i;renderRev();}
function revNav(d){revState.view==='grid'?revJumpGrid(d):revStep(d);}
// 总览网格渲染：同色一列，单元按 4/5 比例自适应；色多图少时自动分带（几组颜色上下排列）放大图片
function renderRevGrid(list){
  var colors=revColors();
  var ncols=colors.length;
  var maxRows=0;
  colors.forEach(function(c){if(c.items.length>maxRows)maxRows=c.items.length;});
  var gap=10,bandGap=16,padX=40,topH=54,bottomPad=20;
  var availW=window.innerWidth-padX-20, availH=window.innerHeight-topH-bottomPad-12;
  // 选最优分带数 B：列数=ceil(色数/B)，行数=B*每色张数；单元宽取 宽约束 与 高约束(4/5) 的较小值，B 使单元最大者胜
  var best=null;
  for(var B=1;B<=ncols;B++){
    var colsB=Math.ceil(ncols/B);
    var rowsB=maxRows*B;
    var wB=Math.floor(Math.min((availW-(colsB-1)*gap)/colsB,(availH-(rowsB-1)*gap-(B-1)*bandGap-24*B)/(rowsB*1.25)));
    if(wB>=80&&(!best||wB>best.w))best={B:B,cols:colsB,rows:rowsB,w:wB};
  }
  if(!best)best={B:1,cols:ncols,rows:maxRows,w:Math.max(80,Math.floor((availW-(ncols-1)*gap)/ncols))};
  var cellW=Math.min(520,best.w), cellH=Math.floor(cellW*1.25);
  document.getElementById('revDx').textContent=revState.dx;
  document.getElementById('revName').textContent='点击任意图看大图；←/→ 换款；Esc 关闭';
  document.getElementById('revCount').textContent=list.length+' 张 · '+ncols+' 色';
  // 按 best.cols 把颜色切成若干带（每带一行颜色列，同色仍只在同一列）
  var bands=[];
  for(var i=0;i<colors.length;i+=best.cols)bands.push(colors.slice(i,i+best.cols));
  var html=bands.map(function(band){
    var colsHtml=band.map(function(col){
      var cells=col.items.map(function(it){
        var i2=list.indexOf(it);
        return '<div class="rev-cell" style="width:'+cellW+'px;height:'+cellH+'px" onclick="revState.idx='+i2+';revState.view=\'one\';renderRev()" title="'+it.n+'">'
          +'<img src="/thumb?dx='+revState.dx+'&kind=up&file='+encodeURIComponent(it.n)+'&t='+it.t+'" loading="lazy">'
          +'<button class="rev-cell-del" onclick="event.stopPropagation();revState.idx='+i2+';revDelete(true)" title="删除（送回收站）">×</button>'
          +'<span class="rev-cell-cap">'+it.l+'</span>'
          +'</div>';
      }).join('');
      return '<div class="rev-col"><span class="rev-col-hd">'+col.c+'</span>'+cells+'</div>';
    }).join('');
    return '<div class="rev-band">'+colsHtml+'</div>';
  }).join('');
  document.getElementById('revStage').innerHTML='<div class="rev-gridall">'+html+'</div>';
  document.getElementById('revStrip').style.display='none';
  document.getElementById('revOverviewBtn').style.display='none';
}
// 单图模式渲染
function renderRevOne(list){
  var f=list[revState.idx];
  var dx=revState.dx;
  document.getElementById('revDx').textContent=dx;
  document.getElementById('revName').textContent=f.l+' · '+f.n;
  document.getElementById('revCount').textContent=(revState.idx+1)+' / '+list.length;
  document.getElementById('revStage').innerHTML=
    '<img src="/original?dx='+dx+'&kind=up&file='+encodeURIComponent(f.n)+'&t='+f.t+'">'
    +'<button class="rev-restick" onclick="revResticker()" title="重新贴图（仅本张）">↻</button>'
    +'<button class="rev-del" onclick="revDelete(false)" title="删除 '+f.n+'（送回收站，可撤销）">×</button>'
    +'<span class="rev-cap">'+f.l+'</span>';
  var html=list.map(function(it,i){
    return '<img class="rev-thumb'+(i===revState.idx?' active':'')+'" src="/thumb?dx='+dx+'&kind=up&file='+encodeURIComponent(it.n)+'&t='+it.t+'" onclick="revGo('+i+')" loading="lazy" title="'+it.n+'">';
  }).join('');
  var strip=document.getElementById('revStrip');
  strip.style.display='flex';
  strip.innerHTML=html;
  var cur=strip.children[revState.idx];
  if(cur&&cur.scrollIntoView)cur.scrollIntoView({inline:'center',block:'nearest'});
  document.getElementById('revOverviewBtn').style.display='';
}
function renderRev(){
  var list=revFiles();
  if(!list.length){closeRev();return;}
  if(revState.idx>=list.length)revState.idx=list.length-1;
  if(revState.idx<0)revState.idx=0;
  if(revState.view==='grid')renderRevGrid(list);
  else renderRevOne(list);
}
// stayGrid=true：总览里删图后留在总览
function revDelete(stayGrid){
  var list=revFiles();
  if(!list.length)return;
  var f=list[revState.idx];
  if(!f)return;
  var dx=revState.dx;
  if(!confirm('删除 '+dx+'/up/'+f.n+' ？（送回收站，可撤销）'))return;
  fetch('/del?dx='+dx+'&which=up&file='+encodeURIComponent(f.n)).then(function(r){return r.json();}).then(function(d){
    showToast(d.msg);
    if(d.ok){
      f._deleted=true;
      var item=document.getElementById('up-'+dx+'-'+f.n);
      if(item)item.classList.add('deleted');
      if(!stayGrid&&revState.view!=='grid')revState.view='one';
      renderRev();
    }
  }).catch(function(e){showToast('❌ 请求失败: '+e);});
}
function revResticker(){
  var list=revFiles();
  if(!list.length)return;
  var f=list[revState.idx];
  var dx=revState.dx;
  if(!confirm('重新贴图 '+dx+'/'+f.n+' ？\n仅重新生成这一张，不影响同款其他贴图。'))return;
  showToast('⏳ 正在重新贴图 '+f.n+'…');
  fetch('/resticker?dx='+dx+'&file='+encodeURIComponent(f.n)).then(function(r){return r.json();}).then(function(d){
    showToast(d.msg);
    if(d.ok){
      f.t=Date.now();   // 破缓存
      var item=document.getElementById('up-'+dx+'-'+f.n);
      if(item){var img=item.querySelector('img');if(img)img.src=img.src.split('&t=')[0]+'&t='+f.t;}
      renderRev();
    }
  }).catch(function(e){showToast('❌ 重新贴图请求失败：'+e);});
}
document.addEventListener('keydown',function(e){
  if(!revState.dx)return;
  if(e.key==='Escape'){
    e.stopPropagation();
    if(revState.view==='one'){revState.view='grid';renderRev();}
    else closeRev();
  }
  else if(e.key==='ArrowLeft'){revState.view==='grid'?revJumpGrid(-1):revStep(-1);}
  else if(e.key==='ArrowRight'){revState.view==='grid'?revJumpGrid(1):revStep(1);}
},true);
