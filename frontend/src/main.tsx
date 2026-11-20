import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-600.css';
import './styles/tokens.css';
import './styles/base.css';
import { OperatorScreen } from './OperatorScreen';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><OperatorScreen /></React.StrictMode>,
);
