import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Container, Snackbar } from '@mui/material';

import { apiUrl } from '../../shared/Variables';
import useToken from '../../hooks/useToken';
import useUserData from '../../hooks/useUserData';
import WaitingBase from '../../components/Waiting-base.component';

import UsersDisplay from './user/Users-display.component';

const UserManagementPanel = () => {
  const [users, setUsers] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [refreshData, setRefreshData] = useState(false);
  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();
  const { userData } = useUserData();

  let userDataObj = JSON.parse(userData);

  // API
  async function getUsers() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/user/list',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setUsers(response.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving user data from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving user data from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Retrieve data
  useEffect(() => {
    getUsers();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getUsers();
    setLoadingData(false);
  }

  return (
    <div style={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
      {userDataObj.is_admin ? (
        <>
          <Container maxWidth="lg">
            {!loadingData ? (
              <UsersDisplay users={users} apiUrl={apiUrl} setRefreshData={setRefreshData.bind()} />
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
        </>
      ) : (
        <Container>
          <Alert severity="error" variant="outlined" sx={{ width: '100%' }}>
            You must be an administrator to access these options.
          </Alert>
        </Container>
      )}
    </div>
  );
};

export default UserManagementPanel;
