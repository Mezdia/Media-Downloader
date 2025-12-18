/**
 * Media Downloader API Layer
 * Handles all communication with the backend.
 */

const API_BASE = '';

class Api {
    static async request(endpoint, options = {}) {
        try {
            const base = (typeof window !== 'undefined' && window.API_BASE) ? window.API_BASE : API_BASE;
            const url = `${base}${endpoint}`;
            const response = await fetch(url, options);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `API Error: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    }

    // --- YouTube Endpoints ---

    static async getYoutubeInfo(url) {
        return this.request(`/info?url=${encodeURIComponent(url)}`);
    }

    static async getYoutubeFormats(url) {
        return this.request(`/formats?url=${encodeURIComponent(url)}`);
    }

    static async getYoutubePlaylist(url) {
        return this.request(`/download/playlist/info?url=${encodeURIComponent(url)}`);
    }

    static async getSubtitles(url, lang = 'all') {
        return this.request(`/subtitles?url=${encodeURIComponent(url)}&lang=${lang}`);
    }

    static async getThumbnail(url, quality = 'maxres') {
        return this.request(`/thumbnail?url=${encodeURIComponent(url)}&quality=${quality}`);
    }

    static async startDownload(payload) {
        return this.request('/download/single', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startBatchDownload(payload) {
        return this.request('/download/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async getJobStatus(jobId) {
        return this.request(`/status/${jobId}`);
    }

    static async getAllJobs() {
        return this.request('/jobs');
    }

    static async cancelJob(jobId) {
        return this.request(`/jobs/${jobId}/cancel`, {
            method: 'POST'
        });
    }

    static async getStreamUrl(url, quality = 'best') {
        return this.request(`/stream/video?url=${encodeURIComponent(url)}&quality=${quality}`);
    }

    static async startPlaylistDownloadAll(payload) {
        return this.request('/download/playlist/all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startPlaylistDownloadSelect(payload) {
        return this.request('/download/playlist/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    // --- Instagram Endpoints ---

    static async getIgPostInfo(url) {
        return this.request(`/instagram/post/info?url=${encodeURIComponent(url)}`);
    }

    static async getIgReelInfo(url) {
        return this.request(`/instagram/reel/info?url=${encodeURIComponent(url)}`);
    }

    static async getIgProfileInfo(username) {
        return this.request(`/instagram/profile/info?username=${encodeURIComponent(username)}`);
    }

    static async getIgProfilePosts(username, limit = 12) {
        return this.request(`/instagram/profile/posts?username=${encodeURIComponent(username)}&limit=${limit}`);
    }

    static async getIgStoryInfo(username) {
        return this.request(`/instagram/story/info?username=${encodeURIComponent(username)}`);
    }

    static async startIgPostDownload(payload) {
        return this.request('/instagram/download/post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startIgReelDownload(payload) {
        return this.request('/instagram/download/reel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startIgPostDownload(payload) {
        return this.request('/instagram/download/post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startIgReelDownload(payload) {
        return this.request('/instagram/download/reel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startIgStoriesDownload(payload) {
        return this.request('/instagram/download/story', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async startIgCarouselDownload(payload) {
        return this.request('/instagram/download/carousel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async getIgPostStats(url) {
        return this.request(`/instagram/post/stats?url=${encodeURIComponent(url)}`);
    }

    static async getIgReelStats(url) {
        return this.request(`/instagram/reel/stats?url=${encodeURIComponent(url)}`);
    }

    static async getIgProfilePosts(username, limit = 12) {
        return this.request(`/instagram/profile/posts?username=${encodeURIComponent(username)}&limit=${limit}`);
    }

    static async startIgBatchDownload(payload) {
        return this.request('/instagram/download/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async getIgJobStatus(jobId) {
        return this.request(`/instagram/status/${jobId}`);
    }

    static async getAllIgJobs() {
        return this.request('/instagram/jobs');
    }

    static async cancelIgJob(jobId) {
        return this.request(`/instagram/jobs/${jobId}/cancel`, {
            method: 'POST'
        });
    }

    // --- Helper Methods ---

    static async downloadFile(url) {
        window.open(url, '_blank');
    }

    static async checkHealth() {
        return this.request('/health');
    }
}
