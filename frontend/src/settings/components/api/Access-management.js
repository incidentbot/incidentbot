import React, { useEffect, useState } from 'react';
import axios from 'axios';
import useToken from '../../../hooks/useToken';
import {
  Alert,
  Box,
  Button,
  Container,
  FilledInput,
  FormControl,
  IconButton,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  Snackbar,
  Tooltip,
  Typography
} from '@mui/material';

import { apiUrl } from '../../../shared/Variables';
import WaitingBase from '../../../components/Waiting-base.component';

import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteIcon from '@mui/icons-material/Delete';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

function APIAccessManagement() {
  const { token } = useToken();

  const [loadingData, setLoadingData] = useState(true);
  const [refreshData, setRefreshData] = useState(false);
  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const [apiKey, setApiKey] = useState();
  const [apiAllowedHosts, setApiAllowedHosts] = useState([]);
  const [values, setValues] = useState({});

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const handleClickShowApiKey = () => {
    setValues({
      ...values,
      showApiKey: !values.showApiKey
    });
  };

  const handleMouseDownPassword = (event) => {
    event.preventDefault();
  };

  async function createApiKey() {
    return fetch(`${apiUrl}/auth/api_key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      }
    }).then((data) => data.json());
  }

  const handleSubmitCreateApiKey = async (e) => {
    e.preventDefault();
    const apiKey = await createApiKey();
    if (!apiKey.success) {
      setFetchStatus('error');
      setFetchMessage(`Error creating API key: ${apiKey.error}`);
      setOpenFetchStatus(true);
    } else if (apiKey.success) {
      setFetchStatus('success');
      setFetchMessage('API key created successfully!');
      setOpenFetchStatus(true);
      setRefreshData(true);
    }
  };

  async function createApiAllowedHost() {
    return fetch(`${apiUrl}/auth/api_allowed_hosts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token
      },
      body: JSON.stringify(values)
    }).then((data) => data.json());
  }

  const handleSubmitCreateApiAllowedHost = async (e) => {
    e.preventDefault();
    const apiAllowedHost = await createApiAllowedHost();
    if (!apiAllowedHost.success) {
      setFetchStatus('error');
      setFetchMessage(`Error adding host: ${apiAllowedHost.error}`);
      setOpenFetchStatus(true);
    } else if (apiAllowedHost.success) {
      setFetchStatus('success');
      setFetchMessage('Host added successfully!');
      setOpenFetchStatus(true);
      setRefreshData(true);
    }
  };

  const deleteApiKey = async () => {
    await axios({
      method: 'DELETE',
      responseType: 'json',
      url: apiUrl + '/auth/api_key',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage('API key deleted successfully!');
        setOpenFetchStatus(true);
        setRefreshData(true);
        setApiKey(null);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting API key: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting API key: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  };

  const deleteApiAllowedHost = async (host) => {
    await axios({
      method: 'DELETE',
      responseType: 'json',
      url: apiUrl + '/auth/api_allowed_hosts',
      data: JSON.stringify({ host: host }),
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage('Host removed successfully!');
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error removing host: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error removing host: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  };

  async function getApiKey() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/auth/api_key',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setApiKey(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving data from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving data from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function getApiAllowedHosts() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/auth/api_allowed_hosts',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setApiAllowedHosts(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving data from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving data from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Retrieve data
  useEffect(() => {
    getApiKey();
    getApiAllowedHosts();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    getApiKey();
    getApiAllowedHosts();
    setRefreshData(false);
    setLoadingData(false);
  }

  return (
    <div style={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
      <Container maxWidth="lg">
        {!loadingData ? (
          <>
            <form onSubmit={handleSubmitCreateApiKey}>
              <Container>
                <Typography variant="h5" noWrap component="div" color="primary">
                  API Token
                </Typography>
                <Typography variant="body1" noWrap component="div" color="primary">
                  This API key will allow access to the API for integrating with other services.
                  Keep it secure. Regenerate it if you lose it.
                </Typography>
                <Box display="flex" alignItems="center">
                  <FormControl sx={{ width: { xs: '100%', md: '50%' } }} variant="outlined">
                    <FilledInput
                      disabled
                      id="apiKey"
                      type={values.showApiKey ? 'text' : 'password'}
                      value={apiKey === undefined ? '' : apiKey}
                      onChange={handleChange('password')}
                      placeholder="API key will appear here"
                      endAdornment={
                        <>
                          <InputAdornment position="end">
                            <IconButton
                              aria-label="copy key"
                              onClick={() => {
                                navigator.clipboard.writeText(apiKey);
                              }}
                              edge="end">
                              <ContentCopyIcon />
                            </IconButton>
                          </InputAdornment>
                          <InputAdornment position="end">
                            <IconButton
                              aria-label="toggle key visibility"
                              onClick={handleClickShowApiKey}
                              onMouseDown={handleMouseDownPassword}
                              edge="end">
                              {values.showApiKey ? <VisibilityOff /> : <Visibility />}
                            </IconButton>
                          </InputAdornment>
                        </>
                      }
                      label="Password"
                    />
                  </FormControl>
                </Box>
                <FormControl>
                  <Box display="flex" sx={{ marginTop: 1 }}>
                    <Button variant="contained" size="large" color="info" type="submit">
                      {apiKey === null ? 'Generate' : 'Regenerate'}
                    </Button>
                    {apiKey !== null && (
                      <Button
                        variant="contained"
                        size="large"
                        color="error"
                        onClick={deleteApiKey}
                        sx={{ marginLeft: 1 }}>
                        Disable
                      </Button>
                    )}
                  </Box>
                </FormControl>
              </Container>
            </form>
            <form onSubmit={handleSubmitCreateApiAllowedHost}>
              <Container sx={{ marginTop: 4 }}>
                <Typography variant="h5" noWrap component="div" color="primary">
                  Allowed Subnets
                </Typography>
                <Typography variant="body1" noWrap component="div" color="primary">
                  Endpoints originating in these subnets will be able to use the API.
                </Typography>
                <Box>
                  <div>
                    <List>
                      {apiAllowedHosts.map((host, i) => (
                        <ListItem
                          key={i}
                          disablePadding
                          secondaryAction={
                            <Tooltip title="Delete">
                              <IconButton onClick={() => deleteApiAllowedHost(host)}>
                                <DeleteIcon fontSize="medium" />
                              </IconButton>
                            </Tooltip>
                          }>
                          <ListItemText primary={host} />
                        </ListItem>
                      ))}
                    </List>
                  </div>
                </Box>
                <Box display="flex" alignItems="center">
                  <FormControl sx={{ width: { xs: '100%', md: '50%' } }} variant="outlined">
                    <FilledInput
                      required
                      id="host"
                      type="text"
                      value={values.host}
                      onChange={handleChange('host')}
                      placeholder="Host IP CIDR, e.g. 10.10.11.12/24"
                      label="Host"
                    />
                  </FormControl>
                </Box>
                <FormControl>
                  <Box display="flex" sx={{ marginTop: 1 }}>
                    <Button variant="contained" size="large" color="info" type="submit">
                      Add
                    </Button>
                  </Box>
                </FormControl>
              </Container>
            </form>
          </>
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
}

export default APIAccessManagement;
