import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  Divider,
  IconButton,
  Snackbar,
  Tooltip,
  Typography,
  Zoom
} from '@mui/material';

import CodeEditor from '@uiw/react-textarea-code-editor';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDarkReasonable } from 'react-syntax-highlighter/dist/esm/styles/hljs';

import AddSettingSlide from './components/Add-settings-modal.component';
import DeleteSettingDialog from './components/Delete-setting-modal.component';
import WaitingBase from '../components/Waiting-base.component';
import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';
import useUserData from '../hooks/useUserData';
import { tryParseJSONObject } from './components/Shared';

import ClearIcon from '@mui/icons-material/Clear';
import DoneIcon from '@mui/icons-material/Done';
import EditIcon from '@mui/icons-material/Edit';
import GroupIcon from '@mui/icons-material/Group';
import SettingsIcon from '@mui/icons-material/Settings';

import UsersDisplay from './components/Users-display.component';
import OverviewFlow from './components/Incident-workflow.component';

const Settings = () => {
  const [settings, setSettings] = useState([]);
  const [users, setUsers] = useState([]);
  const [pendingChanges, setPendingChanges] = useState(false);
  const [refreshData, setRefreshData] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  const [valueBeingEdited, setValueBeingEdited] = useState('');
  const [editedValuePlaceholder, setEditedValuePlaceholder] = useState('');

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();
  const { userData } = useUserData();

  let userDataObj = JSON.parse(userData);

  // API
  async function getSettings() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/setting',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setSettings(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(
            `Error retrieving settings data from backend: ${error.response.data.error}`
          );
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving settings data from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

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

  async function getPendingChanges() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/setting/application_state',
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setPendingChanges(response.data.data.pending_changes);
      })
      .catch(function (error) {
        if (error.response) {
          console.log(error.response.data.error);
        } else if (error.request) {
          console.log(error);
        }
      });
  }

  async function setPendingChangesFlagInDB(state) {
    await axios({
      method: 'PATCH',
      responseType: 'json',
      url: apiUrl + '/setting/application_state',
      data: JSON.stringify({
        value: JSON.stringify({
          pending_changes: state
        })
      }),
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Setting edited.`);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error editing setting: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error editing setting: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function editSetting(settingName, newValue) {
    await axios({
      method: 'PATCH',
      responseType: 'json',
      url: apiUrl + '/setting/' + settingName,
      data: JSON.stringify({ value: newValue }),
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Setting edited.`);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error editing setting: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error editing setting: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function deleteSetting(settingName) {
    await axios({
      method: 'DELETE',
      responseType: 'json',
      url: apiUrl + '/setting/' + settingName,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Setting deleted.`);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting setting: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting setting: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Interactions
  const handleClickEdit = (settingName) => {
    setValueBeingEdited(settingName);
  };

  const handleClickDone = (settingName) => {
    let isValidJson = tryParseJSONObject(editedValuePlaceholder);
    if (!isValidJson) {
      setFetchStatus('error');
      setFetchMessage(`Value for ${settingName} is not valid JSON.`);
      setOpenFetchStatus(true);
    } else {
      editSetting(settingName, editedValuePlaceholder);
      setValueBeingEdited('');
      setEditedValuePlaceholder('');
      setPendingChangesFlagInDB(true);
    }
  };

  const handleClickCancel = () => {
    setValueBeingEdited('');
    setEditedValuePlaceholder('');
  };

  const handleClickDelete = (settingName) => {
    deleteSetting(settingName);
    setValueBeingEdited('');
  };
  // Retrieve on-call data
  useEffect(() => {
    getSettings();
    getUsers();
    getPendingChanges();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getSettings();
    getUsers();
    getPendingChanges();
    setLoadingData(false);
  }

  return (
    <div style={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
      {userDataObj.is_admin ? (
        <>
          <Container maxWidth="lg">
            <Card elevation={3}>
              <Box sx={{ margin: 1 }}>
                <Typography
                  variant="h5"
                  noWrap
                  component="div"
                  color="primary"
                  sx={{ display: { xs: 'none', md: 'flex' } }}>
                  <SettingsIcon fontSize="large" color="primary" sx={{ marginRight: 1 }} />
                  Workflows
                </Typography>
              </Box>
              <Alert severity="info" variant="outlined" sx={{ width: '100%', marginBottom: 2 }}>
                This is a visual representation of the process that is followed when an incident is
                initiated. <b>This is a beta implementation and for now is read-only.</b>
              </Alert>
              <Container style={{ width: '100%', height: '400px' }}>
                <OverviewFlow />
              </Container>
            </Card>
          </Container>

          <Divider sx={{ margin: 2 }} />
          <Container maxWidth="lg">
            <Box sx={{ marginBottom: 1 }}>
              <Typography
                variant="h5"
                noWrap
                component="div"
                color="primary"
                sx={{ display: { xs: 'none', md: 'flex' } }}>
                <SettingsIcon fontSize="large" color="primary" sx={{ marginRight: 1 }} />
                Application Settings
              </Typography>
            </Box>
            {!loadingData && pendingChanges ? (
              <Alert severity="error" variant="filled" sx={{ width: '100%', marginBottom: 2 }}>
                There are pending changes that will not be applied until the application restarts.
                <Button variant="contained" color="warning" size="small" sx={{ marginLeft: 2 }}>
                  Restart
                </Button>
              </Alert>
            ) : (
              <Alert severity="info" variant="filled" sx={{ width: '100%', marginBottom: 2 }}>
                Any values changed here will not take effect until the next application reload.
              </Alert>
            )}
            <AddSettingSlide setRefreshData={setRefreshData.bind()} />
            {!loadingData ? (
              settings.map((setting, i) => {
                return (
                  <Box key={i} sx={{ marginBottom: 2, marginTop: 2 }}>
                    <Typography
                      variant="h7"
                      sx={{
                        display: { xs: 'none', sm: 'block' },
                        fontFamily: 'Roboto',
                        fontWeight: 100,
                        letterSpacing: '.1rem',
                        color: 'inherit',
                        marginBottom: 1
                      }}>
                      {setting.name.toUpperCase()}
                    </Typography>
                    {setting.description !== undefined && (
                      <Typography
                        variant="subtitle2"
                        sx={{
                          display: { xs: 'none', sm: 'block' },
                          fontFamily: 'Roboto',
                          color: 'inherit',
                          marginBottom: 1
                        }}>
                        {setting.description}
                      </Typography>
                    )}
                    <Box>
                      <Tooltip TransitionComponent={Zoom} title="Edit">
                        <IconButton
                          disabled={valueBeingEdited === setting.name}
                          onClick={() => handleClickEdit(setting.name)}
                          aria-label="edit">
                          <EditIcon
                            color={valueBeingEdited === setting.name ? 'disabled' : 'info'}
                          />
                        </IconButton>
                      </Tooltip>
                      {valueBeingEdited === setting.name && (
                        <>
                          <Tooltip TransitionComponent={Zoom} title="Submit">
                            <IconButton
                              onClick={() => handleClickDone(setting.name)}
                              aria-label="submit">
                              <DoneIcon color="success" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip TransitionComponent={Zoom} title="Cancel">
                            <IconButton
                              onClick={() => handleClickCancel(setting.name)}
                              aria-label="cancel">
                              <ClearIcon color="info" />
                            </IconButton>
                          </Tooltip>
                          <DeleteSettingDialog
                            handleClickDelete={handleClickDelete.bind()}
                            setting={setting}
                          />
                        </>
                      )}
                    </Box>
                    {valueBeingEdited !== setting.name ? (
                      <SyntaxHighlighter
                        language="json"
                        wrapLongLines
                        wrapLines
                        style={atomOneDarkReasonable}>
                        {JSON.stringify(setting.value, null, 4)}
                      </SyntaxHighlighter>
                    ) : (
                      <CodeEditor
                        value={JSON.stringify(setting.value, null, 4)}
                        language="json"
                        onChange={(evn) => setEditedValuePlaceholder(evn.target.value)}
                        padding={6}
                        style={{
                          fontSize: 14,
                          border: '2px dotted',
                          fontFamily:
                            'ui-monospace,SFMono-Regular,SF Mono,Consolas,Liberation Mono,Menlo,monospace'
                        }}
                      />
                    )}
                  </Box>
                );
              })
            ) : (
              <WaitingBase />
            )}
          </Container>

          <Divider sx={{ margin: 2 }} />
          <Container maxWidth="lg">
            <Box sx={{ margin: 1 }}>
              <Typography
                variant="h5"
                noWrap
                component="div"
                color="primary"
                sx={{ display: { xs: 'none', md: 'flex' } }}>
                <GroupIcon fontSize="large" color="primary" sx={{ marginRight: 1 }} />
                User Management
              </Typography>
            </Box>
            <UsersDisplay users={users} apiUrl={apiUrl} setRefreshData={setRefreshData.bind()} />
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

export default Settings;
