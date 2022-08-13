import { Alert, AlertTitle, Box, Grid } from '@mui/material';

const SessionExpiredPage = () => {
  return (
    <div
      style={{
        height: '100vh'
      }}>
      <Grid
        container
        spacing={0}
        direction="column"
        alignItems="center"
        justifyContent="center"
        style={{ minHeight: '20vh' }}>
        <Grid item>
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            sx={{ paddingBottom: 4, paddingTop: 1 }}>
            {' '}
            <Alert severity="error">
              <AlertTitle>Session Expired</AlertTitle>
              Your session has expired. Please login again.
            </Alert>
          </Box>
        </Grid>
      </Grid>
    </div>
  );
};

export default SessionExpiredPage;
