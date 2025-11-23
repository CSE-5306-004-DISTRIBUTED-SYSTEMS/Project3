// Use a relative base so the client will work when served through a reverse proxy (nginx)
// or when backend is available on the same origin. Absolute localhost:5000 breaks when
// the front-end is served through a proxy or different host in production.
const BASE_URL = 'http://localhost:8080/api/';

/**
 * Handles all generic GET/POST API calls.
 * @param {string} endpoint - The API endpoint (e.g., 'inventory', 'gatcha', etc...).
 * @param {string} method - The HTTP method ('GET', 'POST', 'PUT', 'DELETE').
 * @param {Object} bodyData - Data to send with a request.
 * @returns {Promise<Object>} - The JSON response data.
 */
async function callApi(endpoint, method, bodyData = null) {
    const url = BASE_URL + endpoint;
    const fetchOptions = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include' // Always send cookies/session for auth
    };

    if (bodyData) {
        fetchOptions.body = JSON.stringify(bodyData);
    }

    try {
        const response = await fetch(url, fetchOptions);

        // Network-level failure (CORS, DNS, connection refused) will throw and be caught below.
        if (!response.ok) {
            // Try to parse JSON error, but fall back to plain text if not JSON
            let errorText = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                errorText = errorData.message || JSON.stringify(errorData) || errorText;
            } catch (jsonErr) {
                try {
                    const text = await response.text();
                    if (text) errorText = text;
                } catch (textErr) {
                    // ignore - we'll use the status string
                }
            }
            throw new Error(errorText);
        }

        // Some endpoints may return empty response bodies; handle that gracefully
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            // If no JSON, return raw text
            return response.text();
        }

        return response.json();
    } catch (err) {
        // Re-throw with a clearer message for the UI. Keep original error chained via message.
        throw new Error(`Network/Fetch error when calling ${url}: ${err.message}`);
    }
}

// Specific API functions
export const API = {
    // Inventory related APIs
    getInventory: () => callApi('inventory/', 'GET'),
    releasePokemon: (ids) => callApi('release/', 'PUT', { ids }),

    // Catch Pokemon API
    // Use trailing slash to match proxy paths and avoid 301 redirects from nginx
    runGatcha: () => callApi('gatcha/', 'POST'),

    // Trade related APIs
    getTradeData: () => callApi('trade/', 'GET'),
    createTrade: (offering_ids, looking_for_count) => 
        callApi('trade/create/', 'POST', { offering_ids, looking_for_count }), 
    fulfillTrade: (trade_id, fulfilling_ids) => 
        callApi('trade/fulfill/', 'PUT', { trade_id, fulfilling_ids }),

    // User related APIs
    // Server exposes this at /api/user/info
    getUserInfo: () => callApi('user/info', "GET"), 
    
    // Battle related APIs
    getBattleData: () => callApi('battle', 'GET'),
    enterQueue: () => callApi('battle/queue', 'POST')
};