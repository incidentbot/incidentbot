import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Container, Snackbar } from '@mui/material';

import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';
import WaitingBase from '../components/Waiting-base.component';

import Table from './Table';

const Incidents = () => {
  const [incidents, setIncidents] = useState([]);
  const [refreshData, setRefreshData] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [imSettings, setIMSettings] = useState([]);

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  async function getAllIncidents() {
    var url = apiUrl + '/incident';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setIncidents(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving incidents from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving incidents from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function getIMSettings() {
    var url = apiUrl + '/setting/incident_management_configuration';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setIMSettings(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving settings from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving settings from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Retrieve incidents
  useEffect(() => {
    getAllIncidents();
    getIMSettings();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getAllIncidents();
    getIMSettings();
    setLoadingData(false);
  }

  var slackWorkspaceID;
  Object.entries(imSettings).forEach((key) => {
    if (key[0] === 'slack_workspace_id') {
      slackWorkspaceID = key[1];
    }
  });

  return (
    <div className="incidents-page">
      <Container maxWidth="" sx={{ width: '70%', paddingTop: '5vh' }}>
        {!loadingData ? (
          <Table incidents={incidents} slackWorkspaceID={slackWorkspaceID} />
        ) : (
          <WaitingBase />
        )}
      </Container>
      {fetchStatus && (
        <Container>
          <Snackbar
            open={openFetchStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenFetchStatus(false);
            }}>
            <Alert
              severity={fetchStatus ? fetchStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {fetchMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
};

export default Incidents;
