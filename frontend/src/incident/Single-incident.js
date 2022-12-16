import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Container,
  Divider,
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
  Typography
} from '@mui/material';

import { styled } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

import AccessTimeIcon from '@mui/icons-material/AccessTime';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import DeveloperBoardIcon from '@mui/icons-material/DeveloperBoard';
import FindReplaceIcon from '@mui/icons-material/FindReplace';
import ForumIcon from '@mui/icons-material/Forum';
import LabelIcon from '@mui/icons-material/Label';
import MeetingRoomRoundedIcon from '@mui/icons-material/MeetingRoomRounded';
import MilitaryTechIcon from '@mui/icons-material/MilitaryTech';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import PeopleIcon from '@mui/icons-material/People';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import UpdateIcon from '@mui/icons-material/Update';
import WarningIcon from '@mui/icons-material/Warning';

import { Icon } from '@iconify/react';
import { severities, statuses } from '../shared/Variables';
//import { acGradientPerTheme } from '../shared/setTheme';
import { apiUrl } from '../shared/Variables';
import useToken from '../hooks/useToken';

import moment from 'moment';
import AddTagButton from './components/Add-tag.component';
import TagStack from '../components/Tag-stack.component';
import Timeline from './components/Timeline.component';
import WaitingBase from '../components/Waiting-base.component';

const StyledCardHeader = styled(CardHeader)(({ theme }) => ({
  backgroundColor: alpha(theme.palette.primary.dark, 0.2)
}));

const ViewSingleIncident = () => {
  const { incidentName } = useParams();

  const [incident, setIncident] = useState();
  const [pinnedItemsData, setPinnedItemsData] = useState([]);
  const [users, setUsers] = useState([]);
  const [imSettings, setIMSettings] = useState([]);

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
    getIMSettings();
    setLoadingData(false);
  }, []);

  if (refreshData) {
    setLoadingData(true);
    setRefreshData(false);
    getSingleIncident();
    getPinnedItems();
    getSlackUsers();
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
    <div className="view-single-incident-page">
      {!loadingData ? (
        <Container maxWidth="xl" sx={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
          {incident !== undefined ? (
            <>
              <Breadcrumbs
                aria-label="breadcrumb"
                separator={<NavigateNextIcon fontSize="small" />}
                sx={{ paddingBottom: 2 }}>
                <Link
                  underline="hover"
                  sx={{ display: 'flex', alignItems: 'center' }}
                  color="inherit"
                  href="/app/incidents">
                  <Typography
                    variant="h7"
                    sx={{
                      display: { xs: 'none', sm: 'block' },
                      fontFamily: 'Roboto',
                      fontWeight: 100,
                      letterSpacing: '.1rem',
                      color: 'inherit',
                      textDecoration: 'none'
                    }}>
                    INCIDENTS
                  </Typography>
                </Link>
                <Typography
                  variant="subtitle2"
                  sx={{
                    display: { xs: 'none', sm: 'block' },
                    fontFamily: 'Roboto',
                    fontWeight: 100,
                    letterSpacing: '.1rem',
                    color: 'inherit',
                    textDecoration: 'none'
                  }}>
                  {incident.incident_id}
                </Typography>
              </Breadcrumbs>
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
              <Grid container columns={2} spacing={2}>
                <Grid item xs={1}>
                  <Card variant="outlined" sx={{ marginBottom: 2, height: '100%' }}>
                    <StyledCardHeader
                      avatar={<AnnouncementIcon fontSize="medium" sx={{ marginRight: 1 }} />}
                      title={`DETAILS`}
                      titleTypographyProps={{
                        variant: 'h6',
                        fontFamily: 'Roboto',
                        fontWeight: 500,
                        letterSpacing: '.1rem'
                      }}
                    />
                    <List>
                      <ListItem dense key="created_at">
                        <ListItemIcon>
                          <AccessTimeIcon fontSize="large" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Created"
                          secondary={`${moment(incident.created_at, 'YYYY-MM-DDTHH:mm:ss TZ')}`}
                        />
                      </ListItem>
                      <Divider component="li" />
                      <ListItem dense key="updated_at">
                        <ListItemIcon>
                          <UpdateIcon fontSize="large" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Last Update"
                          secondary={`${moment(incident.updated_at, 'YYYY-MM-DDTHH:mm:ss TZ')}`}
                        />
                      </ListItem>
                      <Divider component="li" />
                      <ListItem dense key="status">
                        <ListItemIcon>
                          <FindReplaceIcon fontSize="large" />
                        </ListItemIcon>
                        <FormControl variant="filled" size="small" sx={{ minWidth: 120 }}>
                          <InputLabel id="severity-select">Severity</InputLabel>
                          <Select
                            labelId="severity-select"
                            id="severity-select"
                            value={incident.status}
                            //disabled={waitingForSomething || incident.status === 'resolved'}
                            disabled
                            onChange={() => console.log('changed')}>
                            {statuses.map((status) => [
                              <MenuItem value={status} key={status}>
                                {status}
                              </MenuItem>
                            ])}
                          </Select>
                        </FormControl>
                      </ListItem>
                      <Divider component="li" />
                      <ListItem dense key="severity">
                        <ListItemIcon>
                          <WarningIcon fontSize="large" />
                        </ListItemIcon>
                        <FormControl variant="filled" size="small" sx={{ minWidth: 120 }}>
                          <InputLabel id="severity-select">Severity</InputLabel>
                          <Select
                            labelId="severity-select"
                            id="severity-select"
                            value={incident.severity}
                            //disabled={waitingForSomething || incident.status === 'resolved'}
                            disabled
                            onChange={() => console.log('changed')}>
                            {severities.map((sev) => [
                              <MenuItem value={sev} key={sev}>
                                {sev}
                              </MenuItem>
                            ])}
                          </Select>
                        </FormControl>
                      </ListItem>
                      <Divider component="li" />
                      <ListItem dense key="slack-channel">
                        <ListItemIcon>
                          <Icon icon="bxl:slack" width="35" height="35" />
                        </ListItemIcon>
                        <Button
                          size="small"
                          variant="outlined"
                          key={`${incident.incident_id}-slack-link`}
                          href={`https://${slackWorkspaceID}.slack.com/archives/${incident.channel_id}`}
                          target="new">
                          Open Slack Channel
                        </Button>
                      </ListItem>
                      <Divider component="li" />
                      <ListItem dense key="conference-bridge">
                        <ListItemIcon>
                          <MeetingRoomRoundedIcon fontSize="large" />
                        </ListItemIcon>
                        <Button
                          size="small"
                          variant="outlined"
                          key={`${incident.incident_id}-conference-link`}
                          href={`${incident.conference_bridge}`}
                          target="new">
                          Join Meeting
                        </Button>
                      </ListItem>
                    </List>
                  </Card>
                </Grid>
                <Grid item xs={1}>
                  <Card variant="outlined" sx={{ marginBottom: 2, height: '100%' }}>
                    <StyledCardHeader
                      avatar={<PeopleIcon fontSize="medium" sx={{ marginRight: 1 }} />}
                      title={`ROLES`}
                      titleTypographyProps={{
                        variant: 'h6',
                        fontFamily: 'Roboto',
                        fontWeight: 500,
                        letterSpacing: '.1rem'
                      }}
                    />
                    {waitingForSomething && (
                      <Box sx={{ width: '100%' }}>
                        <LinearProgress />
                      </Box>
                    )}
                    <List>
                      <ListItem dense key="roles">
                        <ListItemIcon>
                          <MilitaryTechIcon fontSize="large" />
                        </ListItemIcon>
                        <FormControl
                          variant="standard"
                          sx={{
                            marginLeft: 2,
                            marginRight: 2,
                            minWidth: 120,
                            display: 'flex'
                          }}>
                          <InputLabel id="commander-select">Commander</InputLabel>
                          <Select
                            labelId="commander-select"
                            id="commander-select"
                            value={incident.commander !== null ? incident.commander : ''}
                            disabled={waitingForSomething || incident.status === 'resolved'}
                            onChange={handleUserAssign({
                              incidentID: incident.incident_id,
                              channelID: incident.channel_id,
                              messageTS: incident.bp_message_ts,
                              role: 'incident_commander'
                            })}>
                            {users.map((user) => [
                              <MenuItem value={user.name} key={user.name}>
                                {user.name}
                              </MenuItem>
                            ])}
                          </Select>
                        </FormControl>
                      </ListItem>
                      <Divider component="li" />
                      <ListItem>
                        <Divider orientation="vertical" flexItem />
                        <ListItemIcon>
                          <DeveloperBoardIcon fontSize="large" />
                        </ListItemIcon>
                        <FormControl
                          variant="standard"
                          sx={{ marginLeft: 2, marginRight: 2, minWidth: 120 }}>
                          <InputLabel id="tech-lead-select">Tech Lead</InputLabel>
                          <Select
                            labelId="tech-lead-select"
                            id="tech-lead-select"
                            value={incident.technical_lead !== null ? incident.technical_lead : ''}
                            disabled={waitingForSomething || incident.status === 'resolved'}
                            onChange={handleUserAssign({
                              incidentID: incident.incident_id,
                              channelID: incident.channel_id,
                              messageTS: incident.bp_message_ts,
                              role: 'technical_lead'
                            })}>
                            {users.map((user) => [
                              <MenuItem value={user.name} key={user.name}>
                                {user.name}
                              </MenuItem>
                            ])}
                          </Select>
                        </FormControl>
                      </ListItem>
                      <Divider component="li" />
                      <ListItem>
                        <Divider orientation="vertical" flexItem />
                        <ListItemIcon>
                          <ForumIcon fontSize="large" />
                        </ListItemIcon>
                        <FormControl
                          variant="standard"
                          sx={{ marginLeft: 2, marginRight: 2, minWidth: 120 }}>
                          <InputLabel id="communications-liaison-select">Comms</InputLabel>
                          <Select
                            labelId="communications-liaison-select"
                            id="communications-liaison-select"
                            value={
                              incident.communications_liaison !== null
                                ? incident.communications_liaison
                                : ''
                            }
                            disabled={waitingForSomething || incident.status === 'resolved'}
                            onChange={handleUserAssign({
                              incidentID: incident.incident_id,
                              channelID: incident.channel_id,
                              messageTS: incident.bp_message_ts,
                              role: 'communications_liaison'
                            })}>
                            {users.map((user) => [
                              <MenuItem value={user.name} key={user.name}>
                                {user.name}
                              </MenuItem>
                            ])}
                          </Select>
                        </FormControl>
                      </ListItem>
                      <Divider component="li" />
                    </List>
                  </Card>
                </Grid>
                <Grid item xs={1}>
                  <Card variant="outlined" sx={{ marginTop: 2, marginBottom: 2, height: '100%' }}>
                    <StyledCardHeader
                      avatar={<LabelIcon sx={{ marginRight: 1 }} />}
                      title={`TAGS`}
                      titleTypographyProps={{
                        variant: 'h6',
                        fontFamily: 'Roboto',
                        fontWeight: 500,
                        letterSpacing: '.1rem'
                      }}
                    />
                    <List>
                      <ListItem
                        key="tags"
                        sx={{
                          width: '100%'
                        }}>
                        {incident.tags !== null ? (
                          <>
                            <TagStack
                              apiUrl={apiUrl}
                              incidentID={incident.incident_id}
                              tags={incident.tags}
                              setRefreshData={setRefreshData.bind()}
                            />
                            <AddTagButton
                              apiUrl={apiUrl}
                              incidentID={incident.incident_id}
                              setRefreshData={setRefreshData.bind()}
                            />
                          </>
                        ) : (
                          <>
                            <Box
                              sx={{
                                display: 'flex',
                                displayDirection: 'row',
                                flexGrow: 1
                              }}>
                              <AddTagButton
                                apiUrl={apiUrl}
                                incidentID={incident.incident_id}
                                setRefreshData={setRefreshData.bind()}
                              />
                            </Box>
                          </>
                        )}
                      </ListItem>
                    </List>
                  </Card>
                </Grid>
                <Grid item xs={1}>
                  <Card variant="outlined" sx={{ marginTop: 2, marginBottom: 2, height: '100%' }}>
                    <StyledCardHeader
                      avatar={<QueryStatsIcon sx={{ marginRight: 1 }} />}
                      title={`RCA`}
                      titleTypographyProps={{
                        variant: 'h6',
                        fontFamily: 'Roboto',
                        fontWeight: 500,
                        letterSpacing: '.1rem'
                      }}
                    />
                    <List>
                      <ListItem
                        key="rca"
                        sx={{
                          width: '100%'
                        }}>
                        {incident.rca !== null ? (
                          <Button variant="outlined" href={incident.rca} target="new">
                            View RCA in Confluence
                          </Button>
                        ) : (
                          <>
                            <Alert color="info" variant="outlined" sx={{ width: '100%' }}>
                              A link to the RCA will appear here once the incident is resolved and
                              one has been generated.
                            </Alert>
                          </>
                        )}
                      </ListItem>
                    </List>
                  </Card>
                </Grid>
              </Grid>
              <Box sx={{ marginTop: 4 }}>
                <Timeline incidentName={incident.incident_id} />
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
                        {
                          <ImageList sx={{ width: '100%' }} cols={4}>
                            {imgData.map((item) => (
                              <ImageListItem key={item.img}>
                                <img src={`${item.img}`} alt={item.title} loading="lazy" />
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
                        }
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
                            <Divider component="li" />
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
