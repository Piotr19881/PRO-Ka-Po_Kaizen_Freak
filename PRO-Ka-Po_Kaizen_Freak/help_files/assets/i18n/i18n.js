/* Simple resource-based i18n loader
   - Exposes global I18n object with setLanguage(lang) and has(lang)
   - Loads JSON files from ./assets/i18n/{lang}.json
   - Replaces textContent of elements with data-i18n="key"
*/
(function(){
    const PREFIX = './assets/i18n/';
    const CACHE = {};
    const current = {lang: null};

    async function load(lang){
        if(CACHE[lang]) return CACHE[lang];
        try{
            const res = await fetch(PREFIX + lang + '.json');
            if(!res.ok) throw new Error('not found');
            const j = await res.json();
            CACHE[lang] = j;
            return j;
        }catch(e){
            return null;
        }
    }

    function translateTo(map){
        const els = document.querySelectorAll('[data-i18n]');
        els.forEach(el=>{
            const key = el.getAttribute('data-i18n');
            if(!key) return;
            const val = map[key];
            if(val === undefined) return;
            // preserve simple HTML tags if present in value
            if(/<[^>]+>/.test(val)) el.innerHTML = val; else el.textContent = val;
        });
    }

    window.I18n = {
        async setLanguage(lang){
            const map = await load(lang);
            if(!map) return false;
            translateTo(map);
            current.lang = lang;
            localStorage.setItem('pkp_lang', lang);
            return true;
        },
        async has(lang){
            const map = await load(lang);
            return !!map;
        },
        get current(){return current.lang}
    };

    // auto-apply saved language
    document.addEventListener('DOMContentLoaded', async ()=>{
        const saved = localStorage.getItem('pkp_lang');
        if(saved) {
            const ok = await I18n.setLanguage(saved);
            // ignore if not available
        }
    });

})();
