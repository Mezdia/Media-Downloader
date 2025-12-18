/**
 * Media Downloader UI Layer
 * Handles DOM manipulation, language switching, and event listeners.
 */

const UI = {
    state: {
        lang: 'en',
        platform: 'youtube', // 'youtube' or 'instagram'
        viewMode: 'visual' // 'visual' or 'json'
    },

    langData: {
        en: {
            title: "Media Downloader API",
            subtitle: "Production-Ready YouTube & Instagram Downloader",
            youtube: "YouTube",
            instagram: "Instagram",
            enterUrl: "Enter URL here...",
            getInfo: "Get Info",
            getFormats: "Get Formats",
            download: "Download",
            visual: "Visual",
            json: "JSON",
            quality: "Quality",
            type: "Type",
            audioFormat: "Audio Format",
            startDownload: "Start Download",
            downloading: "Downloading...",
            completed: "Completed",
            error: "Error",
            video: "Video",
            audio: "Audio",
            best: "Best",
            worst: "Worst",
            playlist: "Playlist",
            profile: "Profile",
            stories: "Stories",
            reels: "Reels",
            posts: "Posts",
            username: "Username",
        },
        fa: {
            title: "دانلودر پیشرفته مدیا",
            subtitle: "دانلودر حرفه‌ای یوتیوب و اینستاگرام",
            youtube: "یوتیوب",
            instagram: "اینستاگرام",
            enterUrl: "آدرس را وارد کنید...",
            getInfo: "دریافت اطلاعات",
            getFormats: "دریافت فرمت‌ها",
            download: "دانلود",
            visual: "تصویری",
            json: "کد JSON",
            quality: "کیفیت",
            type: "نوع",
            audioFormat: "فرمت صدا",
            startDownload: "شروع دانلود",
            downloading: "در حال دانلود...",
            completed: "تکمیل شد",
            error: "خطا",
            video: "ویدیو",
            audio: "صدا",
            best: "بهترین",
            worst: "کمترین",
            playlist: "لیست پخش",
            profile: "پروفایل",
            stories: "استوری‌ها",
            reels: "ریلز",
            posts: "پست‌ها",
            username: "نام کاربری",
        }
    },

    init() {
        this.cacheDOM();
        this.bindEvents();
        this.render();
    },

    cacheDOM() {
        this.dom = {
            body: document.body,
            langSwitch: document.getElementById('lang-switch'),
            platformBtns: document.querySelectorAll('.platform-btn'),
            sections: {
                youtube: document.getElementById('section-youtube'),
                instagram: document.getElementById('section-instagram')
            },
            inputs: {
                ytUrl: document.getElementById('yt-url'),
                igUrl: document.getElementById('ig-url'),
            },
            buttons: {
                ytInfo: document.getElementById('btn-yt-info'),
                igInfo: document.getElementById('btn-ig-info'),
            },
            results: document.getElementById('results-area'),
            loading: document.getElementById('loading-overlay')
        };
    },

    bindEvents() {
        // Language Switch
        this.dom.langSwitch.addEventListener('click', () => this.toggleLang());

        // Platform Switch
        this.dom.platformBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchPlatform(e.currentTarget.dataset.platform));
        });

        // Form Actions
        this.dom.buttons.ytInfo?.addEventListener('click', () => this.handleYtInfo());
        // this.dom.buttons.igInfo?.addEventListener('click', () => this.handleIgInfo());
    },

    toggleLang() {
        this.state.lang = this.state.lang === 'en' ? 'fa' : 'en';
        this.render();
    },

    switchPlatform(platform) {
        this.state.platform = platform;
        this.render();
    },

    render() {
        const { lang, platform } = this.state;
        const t = this.langData[lang];

        // Update Body Dir/Lang
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr';

        // Update Text Content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            if (t[key]) el.textContent = t[key];
        });

        // Update Platform Tabs
        this.dom.platformBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.platform === platform);
        });

        // Show/Hide Sections
        Object.keys(this.dom.sections).forEach(key => {
            if (this.dom.sections[key]) {
                this.dom.sections[key].style.display = key === platform ? 'block' : 'none';
                if (key === platform) {
                    this.dom.sections[key].classList.add('active');
                }
            }
        });
    },

    // --- Action Handlers ---

    async handleYtInfo() {
        const url = this.dom.inputs.ytUrl.value.trim();
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getYoutubeInfo(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    // --- Rendering Helpers ---

    renderResult(data) {
        this.dom.results.innerHTML = '';

        // Render Header with View Toggle
        const header = document.createElement('div');
        header.className = 'result-header';
        header.innerHTML = `
            <h3>Results</h3>
            <div class="view-toggle">
                <button class="toggle-btn ${this.state.viewMode === 'visual' ? 'active' : ''}" onclick="UI.toggleView('visual')">👁️</button>
                <button class="toggle-btn ${this.state.viewMode === 'json' ? 'active' : ''}" onclick="UI.toggleView('json')">{ }</button>
            </div>
        `;
        this.dom.results.appendChild(header);

        // Content Wrapper
        const content = document.createElement('div');
        content.id = 'result-content';
        this.dom.results.appendChild(content);

        this.currentResultData = data; // Store for toggling
        this.updateResultView();
    },

    toggleView(mode) {
        this.state.viewMode = mode;
        // Update buttons
        document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
        // Re-render only content
        this.updateResultView();
        // Manually update active class (simple hack for now or re-render header)
        // Actually renderResult re-creates header, so we just need to update content.
        // Let's just re-render result completely or simple DOM update
        const btns = document.querySelectorAll('.toggle-btn');
        if (btns[0]) btns[0].classList.toggle('active', mode === 'visual');
        if (btns[1]) btns[1].classList.toggle('active', mode === 'json');
    },

    updateResultView() {
        const container = document.getElementById('result-content');
        if (!container || !this.currentResultData) return;

        if (this.state.viewMode === 'json') {
            container.innerHTML = `<div class="json-viewer"><pre>${this.syntaxHighlight(this.currentResultData)}</pre></div>`;
        } else {
            // Visual Mode
            container.innerHTML = this.createVisualCard(this.currentResultData);
        }
    },

    createVisualCard(data) {
        // Handle Video/Playlist/Instagram types
        const thumbnail = data.thumbnail || data.thumbnails?.[0]?.url || '';
        const title = data.title || data.caption || 'No Title';
        const duration = data.duration_string || data.duration || '';

        return `
            <div class="visual-card">
                <div class="card-media">
                    ${thumbnail ? `<img src="${thumbnail}" alt="${title}">` : ''}
                </div>
                <div class="card-info">
                    <h3>${title}</h3>
                    <div class="card-meta">
                        ${duration ? `<span>🕒 ${duration}</span>` : ''}
                        ${data.view_count ? `<span>👁️ ${data.view_count}</span>` : ''}
                        ${data.uploader ? `<span>👤 ${data.uploader}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    },

    showLoading(show) {
        this.dom.loading.classList.toggle('show', show);
    },

    showError(msg) {
        this.dom.results.innerHTML = `<div class="error-msg" style="color: var(--accent-youtube); padding: 1rem; border: 1px solid var(--accent-youtube); border-radius: 0.5rem; background: rgba(239, 68, 68, 0.1);">${msg}</div>`;
    },

    syntaxHighlight(json) {
        if (typeof json != 'string') {
            json = JSON.stringify(json, undefined, 2);
        }
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => UI.init());
