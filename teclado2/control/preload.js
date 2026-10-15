'use strict';
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('control', {
  ask: text => ipcRenderer.invoke('ask', text),
  transcribe: bytes => ipcRenderer.invoke('transcribe', bytes),
  speech: text => ipcRenderer.invoke('speech', text),
  chunks: text => ipcRenderer.invoke('chunks', text),
  cancel: () => ipcRenderer.invoke('cancel'),
  hide: () => ipcRenderer.invoke('hide'),
  ready: () => ipcRenderer.invoke('ready'),
  onCommand: callback => ipcRenderer.on('command', (_event, value) => callback(value)),
  onAutonomy: callback => ipcRenderer.on('autonomy-state', (_event, value) => callback(value)),
});
