"""
Module 2: Next-Gen Prototype-Clean Stealth Polyfill.
Preserves Function.prototype.toString integrity, scrubs CDP execution artifacts,
and injects coherent hardware profiles.
"""

PHANTOM_STEALTH_JS = """
(() => {
    // 1. Prototype-Clean Function.prototype.toString Proxy
    const nativeFunctions = new WeakSet();
    const origToString = Function.prototype.toString;

    function makeNative(fn) {
        nativeFunctions.add(fn);
        return fn;
    }

    const cleanToString = function toString() {
        if (nativeFunctions.has(this)) {
            const name = this.name || '';
            return `function ${name}() { [native code] }`;
        }
        return origToString.apply(this, arguments);
    };
    makeNative(cleanToString);

    try {
        Object.defineProperty(Function.prototype, 'toString', {
            value: cleanToString,
            configurable: true,
            writable: true
        });
    } catch (e) {}

    // 2. Scrub CDP automation artifacts from window and document
    try {
        const cdpKeys = Object.keys(window).filter(k => k.includes('cdc_') || k.includes('__puppeteer') || k.includes('__playwright'));
        for (const k of cdpKeys) {
            delete window[k];
        }
    } catch (e) {}

    // 3. Remove navigator.webdriver cleanly at the prototype level
    try {
        delete Navigator.prototype.webdriver;
        const webdriverGetter = function webdriver() { return false; };
        makeNative(webdriverGetter);
        Object.defineProperty(navigator, 'webdriver', {
            get: webdriverGetter,
            configurable: true
        });
    } catch (e) {}

    // 4. Authentic window.chrome object
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.app = window.chrome.app || { isInstalled: false };
    window.chrome.csi = window.chrome.csi || makeNative(function csi() { return {}; });
    window.chrome.loadTimes = window.chrome.loadTimes || makeNative(function loadTimes() { return {}; });
    window.chrome.runtime = window.chrome.runtime || {
        id: undefined,
        connect: makeNative(function connect() {}),
        sendMessage: makeNative(function sendMessage() {}),
        onMessage: {
            addListener: makeNative(function addListener() {}),
            removeListener: makeNative(function removeListener() {})
        }
    };

    // 5. Coherent Hardware Properties (Chrome 131 on Linux/Windows)
    try {
        const getCores = makeNative(function hardwareConcurrency() { return 8; });
        const getMem = makeNative(function deviceMemory() { return 8; });
        const getTouch = makeNative(function maxTouchPoints() { return 0; });
        const getLangs = makeNative(function languages() { return ['en-US', 'en']; });

        Object.defineProperty(navigator, 'hardwareConcurrency', { get: getCores, configurable: true });
        Object.defineProperty(navigator, 'deviceMemory', { get: getMem, configurable: true });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: getTouch, configurable: true });
        Object.defineProperty(navigator, 'languages', { get: getLangs, configurable: true });
    } catch (e) {}

    // 6. WebGL Vendor & Renderer Spoofing
    try {
        const origGetParam = WebGLRenderingContext.prototype.getParameter;
        const fakeGetParam = function getParameter(param) {
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) return 'Google Inc. (NVIDIA)';
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            return origGetParam.apply(this, arguments);
        };
        makeNative(fakeGetParam);
        WebGLRenderingContext.prototype.getParameter = fakeGetParam;

        if (typeof WebGL2RenderingContext !== 'undefined') {
            const origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
            const fakeGetParam2 = function getParameter(param) {
                if (param === 37445) return 'Google Inc. (NVIDIA)';
                if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return origGetParam2.apply(this, arguments);
            };
            makeNative(fakeGetParam2);
            WebGL2RenderingContext.prototype.getParameter = fakeGetParam2;
        }
    } catch (e) {}

    // 7. Canvas 2D Micro-Jitter (Scrambles tracker hashes without visual distortion)
    try {
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const fakeToDataURL = function toDataURL() {
            const ctx = this.getContext('2d');
            if (ctx && this.width > 8 && this.height > 8) {
                try {
                    const img = ctx.getImageData(0, 0, 1, 1);
                    img.data[0] = img.data[0] ^ 1;
                    ctx.putImageData(img, 0, 0);
                } catch (err) {}
            }
            return origToDataURL.apply(this, arguments);
        };
        makeNative(fakeToDataURL);
        HTMLCanvasElement.prototype.toDataURL = fakeToDataURL;
    } catch (e) {}
})();
"""


def get_stealth_script() -> str:
    """Returns the comprehensive prototype-clean stealth injection script."""
    return PHANTOM_STEALTH_JS
