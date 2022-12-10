import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  Input,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Snackbar
} from '@mui/material';

import { styled } from '@mui/material/styles';
import { red } from '@mui/material/colors';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import AddIcon from '@mui/icons-material/Add';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import Move from '../shared/Move';
import useToken from '../hooks/useToken';

const CreateIncidentButton = styled(Button)(({ theme }) => ({
  color: theme.palette.getContrastText(red[600]),
  backgroundColor: red[700],
  '&:hover': {
    backgroundColor: red[500]
  }
}));

export default function IncidentCreateModal(props) {
  const [loadingData, setLoadingData] = useState(false);
  const [values, setValues] = useState({
    description: '',
    user: '',
    severity: '',
    security: ''
  });

  const { token } = useToken();

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const [open, setOpen] = useState(false);
  const [firstLoad, setFirstLoad] = useState(false);
  const handleOpen = () => {
    setOpen(true), setFirstLoad(true);
  };
  const handleClose = () => setOpen(false);

  const [createIncidentStatus, setCreateIncidentStatus] = useState('');
  const [createIncidentMessage, setCreateIncidentMessage] = useState('');
  const [openCreateIncidentStatus, setOpenCreateIncidentStatus] = useState(false);

  async function createIncident(values) {
    return fetch(`${props.apiUrl}/incident`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(values)
    }).then((data) => data.json());
  }

  const handleSubmit = async (e) => {
    setLoadingData(true);
    e.preventDefault();
    const incident = await createIncident({
      description: `${values.description}`,
      user: `${values.user}`,
      severity: `${values.severity}`,
      security: `${values.security}`
    });
    if (!incident.success) {
      setCreateIncidentStatus('error');
      setCreateIncidentMessage(`Error creating incident: ${incident.error}`);
      setOpenCreateIncidentStatus(true);
    } else if (incident.success) {
      setCreateIncidentStatus('success');
      setCreateIncidentMessage('Incident created successfully!');
      setOpenCreateIncidentStatus(true);
      setOpen(false);
      window.location.reload();
    }
  };

  // Fetch users
  const [users, setUsers] = useState([]);

  async function getSlackUsers() {
    var url = props.apiUrl + '/user/slack_users';
    await axios({
      method: 'GET',
      responseType: 'json',
      url: url,
      headers: {
        Authorization: 'Bearer ' + token,
        'Content-Type': 'application/json'
      }
    })
      .then(function (response) {
        setUsers(response.data.data);
      })
      .catch(function (error) {
        if (error.response) {
          console.log(error.response);
        } else if (error.request) {
          console.log(error.request);
        }
      });
  }

  // Retrieve users only when modal is opened
  useEffect(() => {
    if (open && firstLoad) getSlackUsers();
  }, [open, firstLoad]);

  return (
    <div>
      <Button onClick={handleOpen} variant="contained" color="error" endIcon={<AddIcon />}>
        New Incident
      </Button>
      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>
          <NotificationsActiveIcon sx={{ marginRight: 2 }} />
          Create a New Incident
        </DialogTitle>
        <DialogContent sx={{ margin: 1 }}>
          <p>
            This will declare a new incident and kick off the incident management workflow in Slack.
          </p>
          <p>
            Select your name from the user select below before submitting. You will be automatically
            invited to the incident channel where you can then page on-call, add other participants,
            etc.
          </p>
        </DialogContent>
        <DialogContent>
          <form onSubmit={handleSubmit}>
            <Box display="flex" justifyContent="center" alignItems="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <InputLabel htmlFor="description">Description</InputLabel>
                <Input
                  required
                  placeholder="api timeouts, login issues, etc."
                  id="description"
                  type="text"
                  value={values.description}
                  onChange={handleChange('description')}
                  label="Description"
                />
              </FormControl>
            </Box>
            <Box display="flex" justifyContent="center" alignItem="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <InputLabel id="user">User</InputLabel>
                <Select
                  required
                  labelId="user"
                  id="user"
                  value={values.user}
                  label="User"
                  onChange={handleChange('user')}>
                  {users.map((user) => [
                    <MenuItem value={user.id} key={user.name}>
                      {user.name}
                    </MenuItem>
                  ])}
                </Select>
              </FormControl>
            </Box>
            <Box display="flex" justifyContent="center" alignItem="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <InputLabel id="severity">Severity</InputLabel>
                <Select
                  required
                  labelId="severity"
                  id="severity"
                  value={values.severity}
                  label="Severity"
                  onChange={handleChange('severity')}>
                  {props.severities.map((sev) => [
                    <MenuItem value={sev} key={sev}>
                      {sev.toUpperCase()}
                    </MenuItem>
                  ])}
                </Select>
              </FormControl>
            </Box>
            <Box display="flex" justifyContent="center" alignItem="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <FormLabel id="set-security">Security Related Incident</FormLabel>
                <RadioGroup
                  row
                  aria-labelledby="set-security"
                  defaultValue="false"
                  name="radio-buttons-group"
                  onChange={handleChange('security')}>
                  <FormControlLabel value="false" control={<Radio />} label="False" />
                  <FormControlLabel value="true" control={<Radio />} label="True" />
                </RadioGroup>
              </FormControl>
            </Box>
            <DialogActions sx={{ marginTop: 2 }}>
              <FormControl>
                {loadingData ? (
                  <CircularProgress />
                ) : (
                  <Move
                    rotation={0}
                    timing={1000}
                    scale={1.05}
                    springConfig={{ tension: 150, friction: 5 }}>
                    <CreateIncidentButton
                      size="large"
                      endIcon={<AddCircleOutlineIcon />}
                      type="submit">
                      CREATE
                    </CreateIncidentButton>
                  </Move>
                )}
              </FormControl>
            </DialogActions>
          </form>
        </DialogContent>
      </Dialog>
      {createIncidentStatus && (
        <Container>
          <Snackbar
            open={openCreateIncidentStatus}
            autoHideDuration={6000}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            onClose={(event, reason) => {
              if (reason === 'clickaway') {
                return;
              }
              setOpenCreateIncidentStatus(false);
            }}>
            <Alert
              severity={createIncidentStatus ? createIncidentStatus : 'info'}
              variant="filled"
              sx={{ width: '100%' }}>
              {createIncidentMessage}
            </Alert>
          </Snackbar>
        </Container>
      )}
    </div>
  );
}
