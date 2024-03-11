import { useState } from 'react';
// import axios from 'axios';
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
  Input,
  InputLabel,
  Snackbar
} from '@mui/material';

import AddIcon from '@mui/icons-material/Add';
import DoneIcon from '@mui/icons-material/Done';
import EventNoteIcon from '@mui/icons-material/EventNote';
import useToken from '../../hooks/useToken';

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { DemoContainer } from '@mui/x-date-pickers/internals/demo';
import { LocalizationProvider } from '@mui/x-date-pickers';

dayjs.extend(utc);

export default function AddTimelineEventModal(props) {
  const [loadingData, setLoadingData] = useState(false);

  const onDatePicked = (event) => {
    setValues({ ...values, ['timestamp']: `${event.$d.toISOString().split('.')[0]} UTC` });
  };

  const [values, setValues] = useState({
    event: '',
    timestamp: '',
    user: ''
  });

  const { token } = useToken();

  const handleChange = (prop) => (event) => {
    setValues({ ...values, [prop]: event.target.value });
  };

  const [open, setOpen] = useState(false);
  const handleOpen = () => {
    setOpen(true);
  };
  const handleClose = () => setOpen(false);

  const [fetchStatus, setFetchStatus] = useState('');
  const [fetchMessage, setFetchMessage] = useState('');
  const [openFetchStatus, setOpenFetchStatus] = useState(false);

  async function createEvent(values) {
    return fetch(`${props.apiUrl}/incident/${props.incidentName}/audit`, {
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
    const event = await createEvent({
      event: `${values.event}`,
      timestamp: `${values.timestamp}`,
      user: `${values.user}`
    });
    if (!event.success) {
      setFetchStatus('error');
      setFetchMessage(`Error creating event: ${event.error}`);
      setOpenFetchStatus(true);
    } else if (event.success) {
      setFetchStatus('success');
      setFetchMessage('Event created successfully!');
      setOpenFetchStatus(true);
      setOpen(false);
      setLoadingData(false);
      props.setRefreshData(true);
    }
  };

  return (
    <div>
      <Button
        onClick={handleOpen}
        color="info"
        size="large"
        endIcon={<AddIcon />}
        fullWidth
        sx={{
          display: { xs: 'flex', md: 'flex' }
        }}>
        Add
      </Button>
      <Dialog open={open} fullWidth onClose={handleClose}>
        <DialogTitle>
          <EventNoteIcon sx={{ marginRight: 2 }} />
          Add To Incident Timeline
        </DialogTitle>
        <DialogContent sx={{ margin: 1 }}>
          <p>This will add an event to the incident timeline.</p>
        </DialogContent>
        <DialogContent>
          <form onSubmit={handleSubmit}>
            <Box display="flex" justifyContent="center" alignItems="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <InputLabel htmlFor="event">Event</InputLabel>
                <Input
                  required
                  id="event"
                  type="text"
                  value={values.event}
                  onChange={handleChange('event')}
                  label="Event"
                />
              </FormControl>
            </Box>
            <Box display="flex" justifyContent="center" alignItems="center">
              <FormControl sx={{ margin: 1, width: '80%' }} variant="standard">
                <InputLabel htmlFor="user">User</InputLabel>
                <Input
                  required
                  id="user"
                  type="text"
                  value={values.user}
                  onChange={handleChange('user')}
                  label="User"
                />
              </FormControl>
            </Box>
            <Box display="flex" justifyContent="center" alignItems="center">
              <LocalizationProvider dateAdapter={AdapterDayjs}>
                <DemoContainer components={['DateTimePicker']} sx={{ width: '80%' }}>
                  <DateTimePicker label="Timestamp" onChange={onDatePicked} />
                </DemoContainer>
              </LocalizationProvider>
            </Box>
            <DialogActions sx={{ marginTop: 1 }}>
              <FormControl>
                {loadingData ? (
                  <CircularProgress />
                ) : (
                  <Button variant="contained" endIcon={<DoneIcon />} type="submit">
                    Add
                  </Button>
                )}
              </FormControl>
            </DialogActions>
          </form>
        </DialogContent>
      </Dialog>
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
