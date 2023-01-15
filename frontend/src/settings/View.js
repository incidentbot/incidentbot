import React from 'react';
import { Alert, Box, Container, Tab, Tabs, Typography } from '@mui/material';
import PropTypes from 'prop-types';

import useUserData from '../hooks/useUserData';
import APIAccessManagement from './components/api/Access-management';
import OverviewFlow from './components/incident-workflow/Incident-workflow.component';
import UserManagementPanel from './components/Users-view.component';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}>
      {value === index && (
        <Box sx={{ p: 3 }}>
          <Typography>{children}</Typography>
        </Box>
      )}
    </div>
  );
}

TabPanel.propTypes = {
  children: PropTypes.node,
  index: PropTypes.number.isRequired,
  value: PropTypes.number.isRequired
};

function a11yProps(index) {
  return {
    id: `tab-${index}`,
    'aria-controls': `tabpanel-${index}`
  };
}

const Settings = () => {
  const [value, setValue] = React.useState(0);
  const { userData } = useUserData();
  let userDataObj = JSON.parse(userData);

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  return (
    <div style={{ paddingTop: '2vh', paddingBottom: '5vh' }}>
      <Container maxWidth="lg">
        {userDataObj.is_admin ? (
          <>
            <Box sx={{ width: '100%' }}>
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={value} onChange={handleChange} aria-label="basic tabs example">
                  <Tab label="Users" {...a11yProps(0)} />
                  <Tab label="Workflows" {...a11yProps(1)} />
                  <Tab label="API" {...a11yProps(2)} />
                </Tabs>
              </Box>
              <TabPanel value={value} index={0}>
                <UserManagementPanel />
              </TabPanel>
              <TabPanel value={value} index={1}>
                <OverviewFlow />
              </TabPanel>
              <TabPanel value={value} index={2}>
                <APIAccessManagement />
              </TabPanel>
            </Box>
          </>
        ) : (
          <Alert severity="error" variant="outlined" sx={{ width: '100%' }}>
            You must be an administrator to access these options.
          </Alert>
        )}
      </Container>
    </div>
  );
};

export default Settings;
