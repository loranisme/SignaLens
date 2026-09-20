"use strict";

async function enableSidePanel() {
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
}

chrome.runtime.onInstalled.addListener(() => {
  enableSidePanel().catch(() => {});
});
chrome.runtime.onStartup.addListener(() => {
  enableSidePanel().catch(() => {});
});

