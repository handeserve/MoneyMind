// In ui_helpers.js

// Get the loader element once after DOM is loaded
let globalLoader; // Initialize later
document.addEventListener('DOMContentLoaded', () => {
    globalLoader = document.getElementById('global-loader-overlay');
    if (!globalLoader) {
        console.warn("Global loader element 'global-loader-overlay' not found at DOMContentLoaded.");
    }
});

function showGlobalLoader() {
    if (globalLoader) {
        globalLoader.style.display = 'flex';
    } else {
        // Attempt to find it again if it wasn't ready at initial script parse time
        const loader = document.getElementById('global-loader-overlay');
        if (loader) {
            globalLoader = loader; // Cache it
            loader.style.display = 'flex';
        } else {
            console.warn("Global loader element not found. Cannot show loader.");
        }
    }
}

function hideGlobalLoader() {
    if (globalLoader) {
        globalLoader.style.display = 'none';
    } else {
        const loader = document.getElementById('global-loader-overlay');
        if (loader) {
            globalLoader = loader; // Cache it
            loader.style.display = 'none';
        } else {
            console.warn("Global loader element not found. Cannot hide loader.");
        }
    }
}

function showToast(message, type = 'info', duration = 3000) {
    let toastContainer = document.getElementById('toast-container');

    if (!toastContainer) {
        toastContainer = document.querySelector('.toast-container');
    }

    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        // The class 'toast-container' is also added for styling consistency,
        // though the ID is primary for lookup.
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    // Ensure the base class 'toast' is present, then the type-specific class.
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);

    // Delay adding 'show' class to allow CSS transition to take effect.
    // Using a double requestAnimationFrame or a short timeout.
    requestAnimationFrame(() => {
        requestAnimationFrame(() => { 
            toast.classList.add('show');
        });
    });

    if (duration > 0) {
        setTimeout(() => {
            toast.classList.remove('show');
            // Wait for the hide transition to complete before removing the element.
            toast.addEventListener('transitionend', () => {
                // Check if the toast is still a child of the container before removing
                if (toast.parentNode === toastContainer) {
                    toastContainer.removeChild(toast);
                }
                // If the container is empty after removing a toast, it could be removed.
                // However, standard behavior is to keep the container.
                // if (toastContainer.children.length === 0) {
                //     toastContainer.remove(); // Optional: remove container if empty
                // }
            }, { once: true }); // Ensure the event listener is removed after firing.
        }, duration);
    }
}

/**
 * Global helper function for making API calls.
 * Handles global loader, basic error checking, and toast notifications for errors.
 * @param {string} url - The URL to fetch.
 * @param {object} options - Fetch options (method, headers, body, etc.).
 * @param {boolean} [showLoader=true] - Whether to show the global loader during this fetch.
 * @returns {Promise<any>} - The JSON response from the API.
 * @throws {Error} - Throws an error if the fetch fails or response is not ok, to be caught by caller.
 */
async function fetchAPI(url, options = {}, showLoader = true) {
    if (showLoader) showGlobalLoader();
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errorDetail = response.statusText;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorDetail;
            } catch (e) {
                // Ignore if response is not JSON or already handled
            }
            // Translated error message prefix
            throw new Error(`API 错误 (${response.status}): ${errorDetail}`);
        }
        if (response.status === 204) { // No Content
            return null; 
        }
        return await response.json();
    } catch (error) {
        console.error('API Call failed:', url, error.message, options);
        // The error.message will now be in Chinese if it's from the throw new Error above.
        // If it's a different type of error (e.g. network error), it might be in English.
        showToast(error.message, 'error');
        throw error; // Re-throw for the caller to handle if needed (e.g., to stop further processing)
    } finally {
        if (showLoader) hideGlobalLoader();
    }
}
