import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { ThemeProvider } from '@mui/material/styles';
import { keepTheme, setThemeParameters } from './hooks/setTheme';
import { CssBaseline } from '@mui/material';

import App from './App';
import Jobs from './job/View';
import Incidents from './incident/View';
import NotFoundPage from './components/404.component';
import OnCall from './pager/View';
import Settings from './settings/View';
import ViewSingleIncident from './incident/Single-incident';

import LoginPage from './components/Login.component';
import { PrivateRoute } from './shared/PrivateRoute';

import { WithNav } from './shared/WithNav';

import 'bootstrap/dist/css/bootstrap.css';
import './App.css';

import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
keepTheme();
root.render(
  <React.StrictMode>
    <BrowserRouter basename="/app">
      <ThemeProvider theme={setThemeParameters()}>
        <CssBaseline />
        <Routes>
          <Route
            path="/"
            element={
              <PrivateRoute>
                <WithNav>
                  <App />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route
            path="/incidents"
            element={
              <PrivateRoute>
                <WithNav>
                  <Incidents />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route
            path="/incidents/:incidentName"
            element={
              <PrivateRoute>
                <WithNav>
                  <ViewSingleIncident />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route
            path="/on-call"
            element={
              <PrivateRoute>
                <WithNav>
                  <OnCall />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route
            path="/jobs"
            element={
              <PrivateRoute>
                <WithNav>
                  <Jobs />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <PrivateRoute>
                <WithNav>
                  <Settings />
                </WithNav>
              </PrivateRoute>
            }
          />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
