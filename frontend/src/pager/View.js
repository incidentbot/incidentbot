import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';
import OnCallTable from './Table';

import {
  Alert,
  AlertTitle,
  Box,
  Card,
  CardContent,
  CardHeader,
  Container,
  Divider,
  Snackbar
} from '@mui/material';
import WaitingBase from '../components/Waiting-base.component';

import PagerAutoSelect from './components/Auto-select.component';

const OnCall = () => {
  const [onCallData, setOnCallData] = useState();
  const [onCallAutoMapData, setOnCallAutoMapData] = useState();
  const [refreshData, setRefreshData] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  const [fetchOnCallDataStatus, setFetchOnCallDataStatus] = useState('');
  const [fetchOnCallDataMessage, setFetchOnCallDataMessage] = useState('');
  const [openFetchOnCallDataStatus, setOpenFetchOnCallDataStatus] = useState(false);

  const { token } = useToken();

  async function getOnCallData() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/pager',
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setOnCallData(response.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchOnCallDataStatus('error');
          setFetchOnCallDataMessage(
            `Error retrieving on-call data from backend: ${error.response.data.error}`
          );
          setOpenFetchOnCallDataStatus(true);
        } else if (error.request) {
          setFetchOnCallDataStatus('error');
          setFetchOnCallDataMessage(`Error retrieving on-call data from backend: ${error}`);
          setOpenFetchOnCallDataStatus(true);
        }
      });
  }

  async function getOnCallAutoMapData() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/pager/auto_map',
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setOnCallAutoMapData(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchOnCallDataStatus('error');
          setFetchOnCallDataMessage(
            `Error retrieving on-call data from backend: ${error.response.data.error}`
          );
          setOpenFetchOnCallDataStatus(true);
        } else if (error.request) {
          setFetchOnCallDataStatus('error');
          setFetchOnCallDataMessage(`Error retrieving on-call data from backend: ${error}`);
          setOpenFetchOnCallDataStatus(true);
        }
      });
  }

  // Retrieve on-call data
  useEffect(() => {
    getOnCallData();
    getOnCallAutoMapData();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getOnCallData();
    getOnCallAutoMapData();
    setLoadingData(false);
  }

  return (
    <div style={{ paddingTop: '5vh' }}>
      <Container maxWidth="xl" sx={{ width: '70%' }}>
        {onCallData !== undefined &&
          (onCallData.data !== 'feature_not_enabled' ? (
            !loadingData ? (
              <>
                <OnCallTable data={onCallData} />
                <Divider sx={{ margin: 2 }} />
                <Box sx={{ marginTop: 4 }}>
                  <Card>
                    <CardHeader
                      title="Auto Page"
                      subheader="These PagerDuty schedules will automatically be paged on new incidents."
                    />
                    <CardContent>
                      <PagerAutoSelect data={onCallAutoMapData} />
                    </CardContent>
                  </Card>
                </Box>
              </>
            ) : (
              <WaitingBase />
            )
          ) : (
            <Box display="flex" justifyContent="center" alignItems="center">
              <Alert severity="info">
                <AlertTitle>Integration Not Enabled</AlertTitle>
                The PagerDuty integration is not enabled. Enable it to see pager data here and
                integrate it with the rest of the application!
              </Alert>
            </Box>
          ))}
      </Container>
      {fetchOnCallDataStatus && (
        <Container>
          <Snackbar
            open={openFetchOnCallDataStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenFetchOnCallDataStatus(false);
            }}>
            <Alert
              severity={fetchOnCallDataStatus ? fetchOnCallDataStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {fetchOnCallDataMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
};

export default OnCall;
