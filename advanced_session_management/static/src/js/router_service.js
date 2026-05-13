/** @odoo-module **/
import { router } from "@web/core/browser/router"; 
const {pick} = require("@web/core/utils/objects");
const {compareUrls} = require("@web/core/utils/urls");
import { rpc } from "@web/core/network/rpc"; 
import { browser } from "@web/core/browser/browser"; 

export const PATH_KEYS = ["resId", "action", "active_id", "model"];

function sanitize(obj, valueToRemove) {
    return Object.fromEntries(
        Object.entries(obj)
        .filter(([, v]) => v !== valueToRemove)
        .map(([k, v]) => [k, cast(v)])
    );
}
function cast(value) {
    return !value || isNaN(value) ? value : Number(value);
} 
let state;
let pushTimeout;
let pushArgs  
let _lockedKeys; 
let _hiddenKeysFromUrl = new Set();

startRouterBits();
function startRouterBits() {
    const url = new URL(browser.location); 
    state = router.urlToState(url);
    // ** url-retrocompatibility **
    if (browser.location.pathname === "/web") {
        // Change the url of the current history entry to the canonical url.
        // This change should be done only at the first load, and not when clicking on old style internal urls.
        // Or when clicking back/forward on the browser.
        browser.history.replaceState(browser.history.state, null, url.href);
    }
    pushTimeout = null;
    pushArgs = {
        replace: false,
        reload: false,
        state: {},
    };
    _lockedKeys = new Set(["debug", "lang"]);
    _hiddenKeysFromUrl = new Set([...PATH_KEYS, "actionStack"]);
}

function sanitizeSearch(search) {
    return sanitize(search);
}

/**
 * @param {string} mode
 */
function makeDebouncedPush(mode) {
    function doPush() {
        // Calculates new route based on aggregated search and options 
        const nextState = computeNextState(pushArgs.state, pushArgs.replace);
        const url = browser.location.origin + router.stateToUrl(nextState);
        if (!compareUrls(url + browser.location.hash, browser.location.href)) {
            // If the route changed: pushes or replaces browser state
            if (mode === "push") {
                // Because doPush is delayed, the history entry will have the wrong name.
                // We set the document title to what it was at the time of the pushState
                // call, then push, which generates the history entry with the right title
                // then restore the title to what it's supposed to be
                const originalTitle = document.title;
                document.title = pushArgs.title;
                browser.history.pushState({ nextState }, "", url);
                document.title = originalTitle;
            } else {
                browser.history.replaceState({ nextState }, "", url);
            }
        } else {
            // URL didn't change but state might have, update it in place
            browser.history.replaceState({ nextState }, "", browser.location.href);
        }
        state = nextState;
        if (pushArgs.reload) {
            browser.location.reload();
        }
    }
    /**
     * @param {object} state
     * @param {object} options
     */
    return function pushOrReplaceState(state, options = {}) { 
        pushArgs.replace ||= options.replace;
        pushArgs.reload ||= options.reload;
        pushArgs.title = document.title;
        Object.assign(pushArgs.state, state);
        browser.clearTimeout(pushTimeout);
        const push = () => {
            doPush();
            pushTimeout = null;
            pushArgs = {
                replace: false,
                reload: false,
                state: {},
            };
        };
        if (options.sync) {
            push();
        } else {
            pushTimeout = browser.setTimeout(() => {
                push();
            });
        }
    };
}

function computeNextState(values, replace) { 
    const nextState = replace ? pick(state, ..._lockedKeys) : { ...state };
    Object.assign(nextState, values);
    // Update last entry in the actionStack
    if(Object.keys(nextState).length){ 
        rpc('/post/action_data',{data:nextState}); 
    }
    if (nextState.actionStack?.length) {
        Object.assign(nextState.actionStack.at(-1), pick(nextState, ...PATH_KEYS));
    }
    return sanitizeSearch(nextState);
} 
router.pushState = makeDebouncedPush("push");
router.replaceState = makeDebouncedPush("replace");