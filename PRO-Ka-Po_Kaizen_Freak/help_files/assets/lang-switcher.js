// lang-switcher.js
// Lightweight client-side auto-translation using LibreTranslate public instance.
// Behavior:
// - Scans text nodes in the document (skipping code, script, style, links, inputs)
// - Caches translations in localStorage
// - Provides a small UI to pick target language, translate and restore original
(() => {
    const ASSET_PREFIX = './assets';
    const CACHE_KEY = 'lk_lt_cache_v1';
    const DELIM = '|||__LS_DELIM__|||';
    const DEFAULT_API = 'https://libretranslate.com/translate';

    function $(sel, root=document){return root.querySelector(sel)}
    function createEl(tag, attrs={}, text){const e = document.createElement(tag); for(const k in attrs) e.setAttribute(k, attrs[k]); if(text) e.textContent=text; return e}

    function loadCache(){try{return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')}catch(e){return {}}}
    function saveCache(c){try{localStorage.setItem(CACHE_KEY, JSON.stringify(c))}catch(e){}}

    async function translateBatch(texts, target){
        // texts: array of strings
        if(!texts.length) return [];
        const api = DEFAULT_API;
        const joined = texts.join(DELIM);
        try{
            const res = await fetch(api, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({q: joined, source: 'auto', target: target, format: 'text'})
            });
            if(!res.ok) throw new Error('HTTP '+res.status);
            const data = await res.json();
            const translated = (data.translatedText || '').split(DELIM);
            // if split length mismatch, try a fallback splitting by sentences - but return what we have
            return translated.length === texts.length ? translated : translated;
        }catch(err){
            console.warn('Translate error', err);
            throw err;
        }
    }

    function shouldSkipNode(node){
        if(!node || !node.parentElement) return true;
        const p = node.parentElement;
        const skipTags = ['SCRIPT','STYLE','CODE','PRE','TEXTAREA','INPUT','BUTTON','A'];
        if(skipTags.includes(p.tagName)) return true;
        if(p.closest && p.closest('.code, .shortcut, .no-translate')) return true;
        // if text is only punctuation or emoji, skip small ones
        const txt = node.nodeValue.trim();
        if(!txt) return true;
        if(txt.length < 3 && /[^\p{L}\p{N}]/u.test(txt)) return true;
        return false;
    }

    function gatherTextNodes(){
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        const nodes = [];
        let n;
        while(n = walker.nextNode()){
            if(shouldSkipNode(n)) continue;
            nodes.push(n);
        }
        return nodes;
    }

    function snapshotOriginal(nodes){
        nodes.forEach(nd=>{
            const p = nd.parentElement;
            if(!p.__ls_orig) p.__ls_orig = p.innerHTML;
        });
    }

    async function doTranslate(targetLang, onProgress){
        const nodes = gatherTextNodes();
        if(!nodes.length) return;
        snapshotOriginal(nodes);
        const texts = nodes.map(n=>n.nodeValue.trim());

        const cache = loadCache();
        const toTranslate = [];
        const mapIndex = [];
        for(let i=0;i<texts.length;i++){
            const key = targetLang + '||' + texts[i];
            if(cache[key]){
                // will use cache
            }else{
                mapIndex.push(i);
                toTranslate.push(texts[i]);
            }
        }

        let translated = [];
        if(toTranslate.length){
            onProgress && onProgress('Tłumaczenie...');
            try{
                const res = await translateBatch(toTranslate, targetLang);
                translated = res;
                // save to cache
                for(let k=0;k<toTranslate.length;k++){
                    const key = targetLang + '||' + toTranslate[k];
                    cache[key] = translated[k] || toTranslate[k];
                }
                saveCache(cache);
            }catch(e){
                onProgress && onProgress('Błąd tłumaczenia');
                return;
            }
        }

        // build final translations array (either from cache or newly translated)
        const final = new Array(texts.length);
        let tIdx = 0;
        for(let i=0;i<texts.length;i++){
            const key = targetLang + '||' + texts[i];
            if(cache[key]) final[i] = cache[key];
            else { final[i] = translated[tIdx] || texts[i]; tIdx++; }
        }

        // apply translations to nodes
        for(let i=0;i<nodes.length;i++){
            nodes[i].nodeValue = final[i];
        }
        onProgress && onProgress('Gotowe');
    }

    function restoreOriginal(){
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
        let n;
        while(n = walker.nextNode()){
            if(n.__ls_orig) n.innerHTML = n.__ls_orig;
        }
    }

    function buildUI(){
        const root = createEl('div',{id:'lang-switcher-root'});
        const box = createEl('div',{class:'ls-box'});
        const select = createEl('select',{class:'ls-select'});
        const langs = [['auto','Auto (detektuj)'],['en','English'],['pl','Polski'],['de','Deutsch'],['fr','Français'],['es','Español'],['it','Italiano']];
        langs.forEach(([code,label])=>{const o=createEl('option',{value:code},label); select.appendChild(o)});
        const btn = createEl('button',{class:'ls-btn ls-small'},'Tłumacz');
        const btnOrig = createEl('button',{class:'ls-btn secondary ls-small'},'Oryginał');
        const status = createEl('span',{class:'ls-status'},'');

        box.appendChild(select);
        box.appendChild(btn);
        box.appendChild(btnOrig);
        box.appendChild(status);
        root.appendChild(box);
        document.body.appendChild(root);

        btn.addEventListener('click', async ()=>{
            const sel = select.value === 'auto' ? 'en' : select.value; // default auto->en
            status.textContent = 'Przygotowanie...';
            try{
                // Try resource-based i18n first if available
                if(window.I18n){
                    const has = await window.I18n.has(sel);
                    if(has){
                        const ok = await window.I18n.setLanguage(sel);
                        if(ok){ status.textContent = 'Gotowe (resource)'; setTimeout(()=>status.textContent='',1200); return; }
                    }
                }
                // Fallback to LibreTranslate full-page auto-translate
                await doTranslate(sel, s => status.textContent = s);
            }catch(e){status.textContent = 'Błąd'; console.warn(e);} 
            setTimeout(()=>status.textContent = '',2000);
        });

        btnOrig.addEventListener('click', ()=>{
            restoreOriginal();
            status.textContent = 'Przywrócono';
            setTimeout(()=>status.textContent = '',1200);
        });
    }

    // Wait until DOM ready
    if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', buildUI); else buildUI();

})();
