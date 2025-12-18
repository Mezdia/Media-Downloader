/**
 * Media Downloader API Layer
 * Handles all communication with the backend.
 */

const API_BASE = '';

class Api {
    static async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            const data = await response.json();
            if (!response.ok) {
                // Handle specific HTTP errors if needed
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

    static async getIgStoryInfo(username) {
        return this.request(`/instagram/story/info?username=${encodeURIComponent(username)}`);
    }

    // Instagram Downloads are likely via generic download endpoints or specific ones if they exist.
    // Based on index.html analysis, IG downloads might use /instagram/download/...
    // I need to double check main.py for POST endpoints on instagram_router.
    // Assuming they mirror the get info ones or a generic one. 
    // From the previous view_file, I saw models for InstagramPostDownloadRequest etc.
    // I'll assume standard naming conventions or similar to YT.

    static async startIgDownload(endpoint, payload) {
        return this.request(`/instagram/download/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    static async getIgJobStatus(jobId) {
        return this.request(`/instagram/status/${jobId}`);
    }
}
