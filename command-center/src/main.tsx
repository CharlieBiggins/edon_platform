import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import Login from './Login';
import './styles.css';

function Root() { const [authenticated, setAuthenticated] = React.useState(false); return authenticated ? <App /> : <Login onAuthenticated={() => setAuthenticated(true)} />; }
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><Root /></React.StrictMode>);
