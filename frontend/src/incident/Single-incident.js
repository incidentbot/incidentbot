import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import {
  Alert,
  AppBar,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Container,
  FormControl,
  Grid,
  IconButton,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  InputLabel,
  LinearProgress,
  Link,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Select,
  Snackbar,
  Toolbar,
  Typography
} from '@mui/material';

import { alpha } from '@mui/material/styles';
import { apiUrl } from '../shared/Variables';
import { formatRoleName } from '../shared/formatRoleName';
import { styled } from '@mui/material/styles';
import { titleCase } from '../shared/titleCase';

import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

import moment from 'moment';
import useToken from '../hooks/useToken';

import AttachmentImage from './components/Attachment-image.component';
import Timeline from './components/Timeline.component';
import WaitingBase from '../components/Waiting-base.component';

const StyledCardHeader = styled(CardHeader)(({ theme }) => ({
  backgroundColor: alpha(theme.palette.primary.dark, 0),
  color: theme.palette.primary.light
}));

const ViewSingleIncident = () => {
  const { incidentName } = useParams();

  const [incident, setIncident] = useState();
  const [pinnedItemsData, setPinnedItemsData] = useState([]);
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [slackWorkspaceID, setSlackWorkspaceID] = useState();

  const [loadingData, setLoadingData] = useState(true);
  const [refreshData, setRefreshData] = useState(false);
  const [waitingForSomething, setWaitingForSomething] = useState(false);

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  const { token } = useToken();

  const [values, setValues] = useState({
    channel_id: '',
    role: '',
    bp_message_ts: '',
    user: ''
  });

  let imgData = [];
  let txtData = [];

  // Backend API Functions
  async function getSingleIncident() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/incident/' + incidentName,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setIncident(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving incident from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving incidents from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function getPinnedItems() {
    var url = apiUrl + '/incident/' + incidentName + '/pinned';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setPinnedItemsData(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(
            `Error retrieving pinned items from backend: ${error.response.data.error}`
          );
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(
            `Error retrieving pinned items from backend: ${error.response.data.error}`
          );
          setOpenFetchStatus(true);
        }
      });
  }

  async function deletePinnedItem(id) {
    var url = apiUrl + '/incident/' + incidentName + '/pinned/' + id;
    await axios({
      method: 'DELETE',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Delete pinned item successfully!`);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting pinned item: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error deleting pinned item: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function getSlackUsers() {
    var url = apiUrl + '/user/slack_users';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token
      }
    })
      .then(function (response) {
        setUsers(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving users from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving users from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  async function updateIncidentRole(incidentID) {
    var url = apiUrl + '/incident/' + incidentID + '/role';
    setWaitingForSomething(true);
    await axios({
      method: 'POST',
      url: url,
      data: JSON.stringify(values),
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
      .then(function () {
        setFetchStatus('success');
        setFetchMessage(`Successfully updated incident.`);
        setWaitingForSomething(false);
        setOpenFetchStatus(true);
        setRefreshData(true);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error updating user: ${error.response.data.error}`);
          setOpenFetchStatus(true);
          setWaitingForSomething(false);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error updating user: ${error}`);
          setOpenFetchStatus(true);
          setWaitingForSomething(false);
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

  async function getRoles() {
    await axios({
      method: 'GET',
      responseType: 'json',
      url: apiUrl + '/incident/config/roles',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setRoles(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving role data from backend: ${error.response.data.error}`);
          setOpenFetchStatus(true);
        } else if (error.request) {
          setFetchStatus('error');
          setFetchMessage(`Error retrieving role data from backend: ${error}`);
          setOpenFetchStatus(true);
        }
      });
  }

  // Handlers
  const handleUserAssign = (props) => (event) => {
    values.channel_id = props.channelID;
    values.role = props.role;
    values.bp_message_ts = props.messageTS;
    // The request to Slack has to be user ID, not name
    // Names make more sense in presentation
    let userID;
    users.forEach((obj) => {
      if (obj.name === event.target.value) {
        userID = obj.id;
      }
    });
    values.user = userID;
    setValues({ ...values });
    updateIncidentRole(props.incidentID);
  };

  // Retrieve incidents and users
  useEffect(() => {
    getSingleIncident();
    getPinnedItems();
    getSlackUsers();
    getSlackWorkspaceID();
    getRoles();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getSingleIncident();
    getPinnedItems();
    getSlackUsers();
    getSlackWorkspaceID();
    getRoles();
    setLoadingData(false);
  }

  return (
    <div className="view-single-incident-page">
      {!loadingData ? (
        <Container maxWidth="xl" sx={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
          {incident !== undefined ? (
            <>
              <Box sx={{ flexGrow: 1 }}>
                <AppBar color="transparent" elevation={0} position="static">
                  <Toolbar>
                    <Breadcrumbs
                      aria-label="breadcrumb"
                      separator={<NavigateNextIcon fontSize="small" />}
                      sx={{ flexGrow: 1 }}>
                      <Link
                        underline="hover"
                        sx={{ display: 'flex', alignItems: 'center' }}
                        color="inherit"
                        href="/app/incidents">
                        <Typography
                          variant="h7"
                          sx={{
                            fontFamily: 'Roboto',
                            letterSpacing: '.09rem',
                            color: 'inherit'
                          }}>
                          INCIDENTS
                        </Typography>
                      </Link>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontFamily: 'Roboto',
                          fontWeight: 100,
                          color: 'inherit',
                          textDecoration: 'none'
                        }}>
                        {incident.incident_id}
                      </Typography>
                    </Breadcrumbs>
                    <Box sx={{ paddingRight: 1 }}>
                      <Button
                        size="small"
                        disabled={incident.postmortem === null ? true : false}
                        variant="contained"
                        key={`${incident.incident_id}-postmortem-link`}
                        href={incident.postmortem}
                        target="new">
                        Postmortem
                      </Button>
                    </Box>
                    <Box sx={{ paddingRight: 1 }}>
                      <Button
                        size="small"
                        variant="contained"
                        key={`${incident.incident_id}-slack-link`}
                        href={`https://${slackWorkspaceID}.slack.com/archives/${incident.channel_id}`}
                        target="new">
                        Channel
                      </Button>
                    </Box>
                    <Box>
                      <Button
                        size="small"
                        variant="contained"
                        key={`${incident.incident_id}-meeting-link`}
                        href={`${incident.meeting_link}`}
                        target="new">
                        Meeting
                      </Button>
                    </Box>
                  </Toolbar>
                </AppBar>
              </Box>
              {incident.is_security_incident && (
                <Alert severity="error" sx={{ marginBottom: 2 }}>
                  This incident has been flagged as a security incident.
                </Alert>
              )}
              {incident.status === 'resolved' && (
                <Alert severity="warning" sx={{ marginBottom: 2 }}>
                  This incident has been marked as resolved and it cannot be reopened. If there is a
                  new issue, please create a new incident.
                </Alert>
              )}
              <Grid container columns={2} spacing={1}>
                <Grid item xs={12} md={1}>
                  <Card variant="elevation" sx={{ marginBottom: 1, height: '100%' }}>
                    <StyledCardHeader
                      title={`DETAILS`}
                      titleTypographyProps={{
                        variant: 'h7',
                        fontFamily: 'Roboto'
                      }}
                    />
                    <List>
                      <ListItem dense key="created_at">
                        <ListItemText
                          primary="Created"
                          secondary={`${moment(incident.created_at, 'YYYY-MM-DDTHH:mm:ss TZ')}`}
                        />
                      </ListItem>
                      <ListItem dense key="updated_at">
                        <ListItemText
                          primary="Last Update"
                          secondary={`${moment(incident.updated_at, 'YYYY-MM-DDTHH:mm:ss TZ')}`}
                        />
                      </ListItem>
                      <ListItem dense key="status">
                        <ListItemText primary="Status" secondary={titleCase(incident.status)} />
                      </ListItem>
                      <ListItem dense key="severity">
                        <ListItemText
                          primary="Severity"
                          secondary={incident.severity.toUpperCase()}
                        />
                      </ListItem>
                    </List>
                  </Card>
                </Grid>
                <Grid item xs={12} md={1}>
                  <Card variant="elevation" sx={{ marginBottom: 1, height: '100%' }}>
                    <StyledCardHeader
                      title={`ROLES`}
                      titleTypographyProps={{
                        variant: 'h7',
                        fontFamily: 'Roboto'
                      }}
                    />
                    {waitingForSomething && (
                      <Box sx={{ width: '100%' }}>
                        <LinearProgress />
                      </Box>
                    )}
                    <List>
                      {roles.map((role, i) => (
                        <>
                          <ListItem key={i}>
                            <FormControl
                              variant="standard"
                              fullWidth
                              sx={{
                                marginLeft: 1,
                                minWidth: 220,
                                display: 'flex'
                              }}>
                              <InputLabel id={`${role}-select`}>{formatRoleName(role)}</InputLabel>
                              <Select
                                labelId={`${role}-select`}
                                id={`${role}-select`}
                                value={
                                  incident.roles !== null && incident.roles[role] !== null
                                    ? incident.roles[role]
                                    : ''
                                }
                                disabled={waitingForSomething || incident.status === 'resolved'}
                                onChange={handleUserAssign({
                                  incidentID: incident.incident_id,
                                  channelID: incident.channel_id,
                                  messageTS: incident.bp_message_ts,
                                  role: role
                                })}>
                                {users.map((user, i) => [
                                  <MenuItem value={user.name} key={i}>
                                    {user.name}
                                  </MenuItem>
                                ])}
                              </Select>
                            </FormControl>
                          </ListItem>
                        </>
                      ))}
                    </List>
                  </Card>
                </Grid>
              </Grid>
              <Box sx={{ marginTop: 2 }}>
                <Card variant="elevation" sx={{ marginBottom: 1, height: '100%' }}>
                  <StyledCardHeader
                    title={`TIMELINE`}
                    titleTypographyProps={{
                      variant: 'h7',
                      fontFamily: 'Roboto'
                    }}
                  />
                  <Timeline incidentName={incident.incident_id} />
                </Card>
              </Box>
              <Box sx={{ marginTop: 2 }}>
                {pinnedItemsData !== null &&
                  pinnedItemsData.map((item) => {
                    {
                      item.is_image &&
                        imgData.push({
                          id: item.id,
                          img: `${apiUrl}/incident/${incident.incident_id}/pinned/${item.id}`,
                          title: item.title,
                          author: item.user,
                          ts: item.ts
                        });
                    }
                    {
                      !item.is_image &&
                        txtData.push({
                          id: item.id,
                          content: item.content,
                          author: item.user,
                          ts: item.ts
                        });
                    }
                  })}
                {imgData.length > 0 ? (
                  <>
                    <Card sx={{ marginTop: 2 }}>
                      <StyledCardHeader
                        title="Pinned Attachments"
                        subheader="Messages that were pinned and contain attachments"
                      />
                      <CardContent>
                        <ImageList sx={{ width: '100%' }} cols={4}>
                          {imgData.map((item, i) => (
                            <ImageListItem key={i}>
                              <AttachmentImage item={item} token={token} />
                              <ImageListItemBar
                                title={item.title}
                                subtitle={`${item.author} - ${item.ts}`}
                                actionIcon={
                                  <IconButton
                                    sx={{ color: 'rgba(255, 255, 255, 0.44)' }}
                                    aria-label={`info about ${item.title}`}
                                    onClick={() => deletePinnedItem(item.id)}>
                                    <DeleteForeverIcon color="error" />
                                  </IconButton>
                                }
                              />
                            </ImageListItem>
                          ))}
                        </ImageList>
                      </CardContent>
                    </Card>
                  </>
                ) : (
                  <Box>
                    <Alert
                      severity="info"
                      variant="standard"
                      sx={{ marginTop: 1, marginBottom: 1 }}>
                      Images pinned in the incident channel will appear here.
                    </Alert>
                  </Box>
                )}
                {txtData.length > 0 ? (
                  <>
                    <Card sx={{ marginTop: 2 }}>
                      <StyledCardHeader
                        title="Pinned Messages"
                        subheader="Messages that were pinned and do not contain attachments"
                      />
                      <List dense>
                        {txtData.map((item, i) => (
                          <>
                            <ListItem
                              alignItems="flex-start"
                              key={i}
                              secondaryAction={
                                <IconButton
                                  edge="end"
                                  aria-label="delete"
                                  onClick={() => deletePinnedItem(item.id)}>
                                  <DeleteForeverIcon color="error" />
                                </IconButton>
                              }>
                              <ListItemIcon>
                                <Chip
                                  color="primary"
                                  label={item.author}
                                  sx={{ marginRight: 0.7 }}
                                />
                              </ListItemIcon>
                              <ListItemText primary={item.ts} secondary={item.content} />
                            </ListItem>
                          </>
                        ))}
                      </List>
                    </Card>
                  </>
                ) : (
                  <Box>
                    <Alert
                      severity="info"
                      variant="standard"
                      sx={{ marginTop: 1, marginBottom: 1 }}>
                      Messages pinned in the incident channel will appear here.
                    </Alert>
                  </Box>
                )}
              </Box>
            </>
          ) : (
            <Container>
              <Alert
                severity={fetchStatus ? fetchStatus : 'info'}
                variant="outlined"
                sx={{ width: '100%' }}>
                Incident data not found.
              </Alert>
            </Container>
          )}
        </Container>
      ) : (
        <Container sx={{ paddingTop: 5 }}>
          <WaitingBase />
        </Container>
      )}
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

export default ViewSingleIncident;
