/**
 * Media Downloader UI Layer
 * Handles DOM manipulation, language switching, and event listeners.
 */

const UI = {
    state: {
        lang: 'en',
        platform: 'youtube', // 'youtube' or 'instagram'
        viewMode: 'visual', // 'visual' or 'json'
        activeFeature: 'video', // Current active feature tab
        currentResultData: null
    },

    langData: {
        en: {
            title: "Media Downloader API",
            subtitle: "Production-Ready YouTube & Instagram Downloader",
            youtube: "YouTube",
            instagram: "Instagram",
            enterUrl: "Enter URL here...",
            enterPlaylistUrl: "Enter Playlist URL...",
            enterUrls: "Enter URLs (one per line, max 10)",
            getInfo: "Get Info",
            getFormats: "Get Formats",
            getSubtitles: "Get Subtitles",
            getThumbnail: "Get Thumbnail",
            getPosts: "Get Posts",
            download: "Download",
            downloadAll: "Download All",
            startBatch: "Start Batch Download",
            startStream: "Start Stream",
            visual: "Visual",
            json: "JSON",
            quality: "Quality",
            type: "Type",
            audioFormat: "Audio Format",
            language: "Language",
            filterJobs: "Filter Jobs",
            refresh: "Refresh",
            batchItems: "Batch Items (JSON format)",
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
            formats: "Formats",
            subtitles: "Subtitles",
            thumbnail: "Thumbnail",
            batch: "Batch",
            jobs: "Jobs",
            stream: "Stream"
        },
        fa: {
            title: "دانلودر پیشرفته مدیا",
            subtitle: "دانلودر حرفه‌ای یوتیوب و اینستاگرام",
            youtube: "یوتیوب",
            instagram: "اینستاگرام",
            enterUrl: "آدرس را وارد کنید...",
            enterPlaylistUrl: "آدرس لیست پخش را وارد کنید...",
            enterUrls: "آدرس‌ها را وارد کنید (هر خط یک آدرس، حداکثر 10)",
            getInfo: "دریافت اطلاعات",
            getFormats: "دریافت فرمت‌ها",
            getSubtitles: "دریافت زیرنویس‌ها",
            getThumbnail: "دریافت تصویر بندانگشتی",
            getPosts: "دریافت پست‌ها",
            download: "دانلود",
            downloadAll: "دانلود همه",
            startBatch: "شروع دانلود دسته‌جمعی",
            startStream: "شروع پخش",
            visual: "تصویری",
            json: "کد JSON",
            quality: "کیفیت",
            type: "نوع",
            audioFormat: "فرمت صدا",
            language: "زبان",
            filterJobs: "فیلتر وظایف",
            refresh: "تازه‌سازی",
            batchItems: "آیتم‌های دسته‌جمعی (فرمت JSON)",
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
            formats: "فرمت‌ها",
            subtitles: "زیرنویس‌ها",
            thumbnail: "تصویر بندانگشتی",
            batch: "دسته‌جمعی",
            jobs: "وظایف",
            stream: "پخش"
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
            navItems: document.querySelectorAll('.nav-item'),
            sections: {
                youtube: document.getElementById('section-youtube'),
                instagram: document.getElementById('section-instagram')
            },
            featureSections: {
                // YouTube features
                'video': document.getElementById('feature-video'),
                'playlist': document.getElementById('feature-playlist'),
                'formats': document.getElementById('feature-formats'),
                'subtitles': document.getElementById('feature-subtitles'),
                'thumbnail': document.getElementById('feature-thumbnail'),
                'batch': document.getElementById('feature-batch'),
                'jobs': document.getElementById('feature-jobs'),
                'stream': document.getElementById('feature-stream'),
                // Instagram features
                'ig-post': document.getElementById('feature-ig-post'),
                'ig-reel': document.getElementById('feature-ig-reel'),
                'ig-profile': document.getElementById('feature-ig-profile'),
                'ig-stories': document.getElementById('feature-ig-stories'),
                'ig-batch': document.getElementById('feature-ig-batch'),
                'ig-jobs': document.getElementById('feature-ig-jobs')
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

        // Feature Navigation
        this.dom.navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const feature = e.currentTarget.dataset.feature;
                this.switchFeature(feature);
            });
        });

        // YouTube Button Events
        if (document.getElementById('btn-yt-info')) {
            document.getElementById('btn-yt-info').addEventListener('click', () => this.handleYtInfo());
        }
        if (document.getElementById('btn-yt-formats')) {
            document.getElementById('btn-yt-formats').addEventListener('click', () => this.handleYtFormats());
        }
        if (document.getElementById('btn-yt-playlist-info')) {
            document.getElementById('btn-yt-playlist-info').addEventListener('click', () => this.handleYtPlaylistInfo());
        }
        if (document.getElementById('btn-yt-get-formats')) {
            document.getElementById('btn-yt-get-formats').addEventListener('click', () => this.handleYtGetFormats());
        }
        if (document.getElementById('btn-yt-get-subtitles')) {
            document.getElementById('btn-yt-get-subtitles').addEventListener('click', () => this.handleYtGetSubtitles());
        }
        if (document.getElementById('btn-yt-get-thumbnail')) {
            document.getElementById('btn-yt-get-thumbnail').addEventListener('click', () => this.handleYtGetThumbnail());
        }
        if (document.getElementById('btn-yt-batch-download')) {
            document.getElementById('btn-yt-batch-download').addEventListener('click', () => this.handleYtBatchDownload());
        }
        if (document.getElementById('btn-refresh-jobs')) {
            document.getElementById('btn-refresh-jobs').addEventListener('click', () => this.handleRefreshJobs());
        }
        if (document.getElementById('btn-yt-stream')) {
            document.getElementById('btn-yt-stream').addEventListener('click', () => this.handleYtStream());
        }

        // Instagram Button Events
        if (document.getElementById('btn-ig-post-info')) {
            document.getElementById('btn-ig-post-info').addEventListener('click', () => this.handleIgPostInfo());
        }
        if (document.getElementById('btn-ig-reel-info')) {
            document.getElementById('btn-ig-reel-info').addEventListener('click', () => this.handleIgReelInfo());
        }
        if (document.getElementById('btn-ig-profile-info')) {
            document.getElementById('btn-ig-profile-info').addEventListener('click', () => this.handleIgProfileInfo());
        }
        if (document.getElementById('btn-ig-stories-info')) {
            document.getElementById('btn-ig-stories-info').addEventListener('click', () => this.handleIgStoriesInfo());
        }
        if (document.getElementById('btn-ig-batch-download')) {
            document.getElementById('btn-ig-batch-download').addEventListener('click', () => this.handleIgBatchDownload());
        }
        if (document.getElementById('btn-ig-refresh-jobs')) {
            document.getElementById('btn-ig-refresh-jobs').addEventListener('click', () => this.handleIgRefreshJobs());
        }
    },

    toggleLang() {
        this.state.lang = this.state.lang === 'en' ? 'fa' : 'en';
        this.render();
    },

    switchPlatform(platform) {
        this.state.platform = platform;
        // Reset to default feature when switching platforms
        this.state.activeFeature = platform === 'youtube' ? 'video' : 'ig-post';
        this.render();
    },

    switchFeature(feature) {
        this.state.activeFeature = feature;
        this.render();
    },

    render() {
        const { lang, platform, activeFeature } = this.state;
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

        // Show/Hide Main Sections
        Object.keys(this.dom.sections).forEach(key => {
            if (this.dom.sections[key]) {
                this.dom.sections[key].style.display = key === platform ? 'block' : 'none';
                if (key === platform) {
                    this.dom.sections[key].classList.add('active');
                } else {
                    this.dom.sections[key].classList.remove('active');
                }
            }
        });

        // Update Feature Navigation
        this.dom.navItems.forEach(item => {
            const feature = item.dataset.feature;
            item.classList.toggle('active', feature === activeFeature);
        });

        // Show/Hide Feature Sections
        const platformPrefix = platform === 'youtube' ? '' : 'ig-';
        Object.keys(this.dom.featureSections).forEach(key => {
            if (this.dom.featureSections[key]) {
                const isActive = key === `${platformPrefix}${activeFeature}`;
                this.dom.featureSections[key].style.display = isActive ? 'block' : 'none';
                if (isActive) {
                    this.dom.featureSections[key].classList.add('active');
                } else {
                    this.dom.featureSections[key].classList.remove('active');
                }
            }
        });
    },

    // --- Action Handlers ---

    async handleYtInfo() {
        const url = document.getElementById('yt-url').value.trim();
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

    async handleYtFormats() {
        const url = document.getElementById('yt-url').value.trim();
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getYoutubeFormats(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtPlaylistInfo() {
        const url = document.getElementById('yt-playlist-url').value.trim();
        if (!url) return this.showError('Please enter a playlist URL');

        this.showLoading(true);
        try {
            const data = await Api.getYoutubePlaylist(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtGetFormats() {
        const url = document.getElementById('yt-formats-url').value.trim();
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getYoutubeFormats(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtGetSubtitles() {
        const url = document.getElementById('yt-subtitles-url').value.trim();
        const lang = document.getElementById('yt-subtitles-lang').value;
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getSubtitles(url, lang);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtGetThumbnail() {
        const url = document.getElementById('yt-thumbnail-url').value.trim();
        const quality = document.getElementById('yt-thumbnail-quality').value;
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getThumbnail(url, quality);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtBatchDownload() {
        const urlsText = document.getElementById('yt-batch-urls').value.trim();
        const quality = document.getElementById('yt-batch-quality').value;
        if (!urlsText) return this.showError('Please enter URLs');

        const urls = urlsText.split('\n').filter(url => url.trim());
        if (urls.length > 10) return this.showError('Maximum 10 URLs allowed');

        this.showLoading(true);
        try {
            const data = await Api.startBatchDownload({
                urls: urls,
                quality: quality,
                type: 'video'
            });
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleRefreshJobs() {
        this.showLoading(true);
        try {
            const data = await Api.getJobStatus('all'); // This should be implemented in API
            this.renderJobs(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleYtStream() {
        const url = document.getElementById('yt-stream-url').value.trim();
        const quality = document.getElementById('yt-stream-quality').value;
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getStreamUrl(url, quality);
            this.renderStream(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    // Instagram Handlers
    async handleIgPostInfo() {
        const url = document.getElementById('ig-post-url').value.trim();
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getIgPostInfo(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleIgReelInfo() {
        const url = document.getElementById('ig-reel-url').value.trim();
        if (!url) return this.showError('Please enter a URL');

        this.showLoading(true);
        try {
            const data = await Api.getIgReelInfo(url);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleIgProfileInfo() {
        const username = document.getElementById('ig-username').value.trim();
        if (!username) return this.showError('Please enter a username');

        this.showLoading(true);
        try {
            const data = await Api.getIgProfileInfo(username);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleIgStoriesInfo() {
        const username = document.getElementById('ig-stories-username').value.trim();
        if (!username) return this.showError('Please enter a username');

        this.showLoading(true);
        try {
            const data = await Api.getIgStoryInfo(username);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleIgBatchDownload() {
        const itemsText = document.getElementById('ig-batch-items').value.trim();
        if (!itemsText) return this.showError('Please enter batch items');

        try {
            const items = JSON.parse(itemsText);
            if (!Array.isArray(items)) return this.showError('Invalid JSON format');

            this.showLoading(true);
            const data = await Api.startIgBatchDownload(items);
            this.renderResult(data);
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    },

    async handleIgRefreshJobs() {
        this.showLoading(true);
        try {
            const data = await Api.getIgJobStatus('all');
            this.renderJobs(data);
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
                <button class="toggle-btn ${this.state.viewMode === 'visual' ? 'active' : ''}" onclick="UI.toggleView('visual')">👁️ Visual</button>
                <button class="toggle-btn ${this.state.viewMode === 'json' ? 'active' : ''}" onclick="UI.toggleView('json')">{ } JSON</button>
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

    renderJobs(jobs) {
        const container = document.getElementById('jobs-list') || document.getElementById('ig-jobs-list');
        if (!container) return;

        if (!jobs || jobs.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 2rem;">No jobs found</p>';
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="job-item">
                <div class="job-header">
                    <span class="job-id">Job: ${job.job_id}</span>
                    <span class="job-status ${job.status}">${job.status}</span>
                </div>
                <div class="job-progress">
                    <div class="job-progress-bar" style="width: ${job.progress || 0}%"></div>
                </div>
                <div class="job-info">
                    <p><strong>Type:</strong> ${job.type || 'N/A'}</p>
                    <p><strong>Created:</strong> ${job.created_at || 'N/A'}</p>
                    ${job.title ? `<p><strong>Title:</strong> ${job.title}</p>` : ''}
                </div>
                <div class="job-actions">
                    ${job.status === 'completed' ? `
                        <button class="job-btn download" onclick="UI.downloadJobFile('${job.job_id}')">
                            <i class="fas fa-download"></i> Download
                        </button>
                    ` : ''}
                    ${job.status === 'processing' || job.status === 'pending' ? `
                        <button class="job-btn cancel" onclick="UI.cancelJob('${job.job_id}')">
                            <i class="fas fa-times"></i> Cancel
                        </button>
                    ` : ''}
                    <button class="job-btn refresh" onclick="UI.refreshJobStatus('${job.job_id}')">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                </div>
            </div>
        `).join('');
    },

    renderStream(data) {
        const playerContainer = document.getElementById('stream-player');
        const videoElement = document.getElementById('video-stream');
        
        if (playerContainer && videoElement && data.stream_url) {
            playerContainer.style.display = 'block';
            videoElement.src = data.stream_url;
            videoElement.play().catch(e => console.log('Autoplay prevented:', e));
        }
    },

    toggleView(mode) {
        this.state.viewMode = mode;
        // Update buttons
        document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
        // Re-render only content
        this.updateResultView();
        // Manually update active class
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

        let metaHtml = '';
        if (data.view_count) metaHtml += `<span>👁️ ${data.view_count}</span>`;
        if (data.uploader) metaHtml += `<span>👤 ${data.uploader}</span>`;
        if (data.channel) metaHtml += `<span>🎥 ${data.channel}</span>`;
        if (data.duration) metaHtml += `<span>🕒 ${data.duration}</span>`;
        if (data.video_count) metaHtml += `<span>📹 ${data.video_count} videos</span>`;
        if (data.like_count) metaHtml += `<span>❤️ ${data.like_count}</span>`;
        if (data.comment_count) metaHtml += `<span>💬 ${data.comment_count}</span>`;

        return `
            <div class="visual-card">
                <div class="card-media">
                    ${thumbnail ? `<img src="${thumbnail}" alt="${title}">` : '<div style="width: 200px; height: 120px; background: var(--bg-secondary); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center;">No Image</div>'}
                </div>
                <div class="card-info">
                    <h3>${title}</h3>
                    ${metaHtml ? `<div class="card-meta">${metaHtml}</div>` : ''}
                    ${data.description ? `<p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.5rem;">${data.description.substring(0, 200)}${data.description.length > 200 ? '...' : ''}</p>` : ''}
                </div>
            </div>
        `;
    },

    showLoading(show) {
        this.dom.loading.classList.toggle('show', show);
    },

    showError(msg) {
        this.dom.results.innerHTML = `<div class="error-msg"><i class="fas fa-exclamation-circle"></i> ${msg}</div>`;
    },

    showSuccess(msg) {
        this.dom.results.innerHTML = `<div class="success-msg"><i class="fas fa-check-circle"></i> ${msg}</div>`;
    },

    syntaxHighlight(json) {
        if (typeof json != 'string') {
            json = JSON.stringify(json, undefined, 2);
        }
        json = json.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>');
        return json.replace(/("(\u[a-zA-Z0-9]{4}|\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
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
    },

    // Additional helper methods
    downloadJobFile(jobId) {
        // Implement file download logic
        console.log('Download job:', jobId);
    },

    cancelJob(jobId) {
        // Implement job cancellation
        console.log('Cancel job:', jobId);
    },

    refreshJobStatus(jobId) {
        // Implement status refresh
        console.log('Refresh job:', jobId);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => UI.init());
