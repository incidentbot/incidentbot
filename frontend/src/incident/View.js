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
  const [slackWorkspaceID, setSlackWorkspaceID] = useState();

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

  async function getSlackWorkspaceID() {
    var url = apiUrl + '/setting/slack_workspace_id';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setSlackWorkspaceID(response.data.data);
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
    getSlackWorkspaceID();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getAllIncidents();
    getSlackWorkspaceID();
    setLoadingData(false);
  }

  return (
    <div className="incidents-page">
      <Container maxWidth="" sx={{ width: '75%', paddingTop: '4vh' }}>
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
