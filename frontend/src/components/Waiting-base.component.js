import React from 'react';
import { Box, LinearProgress } from '@mui/material';

import AnimatedAppLogo from './Animated-app-logo.component';

const WaitingBase = () => {
  return (
    <div>
      <LinearProgress />
      <Box display="flex" justifyContent="center" sx={{ paddingBottom: 1, paddingTop: 8 }}>
        <AnimatedAppLogo width={80} height={80} duration={1000} />
      </Box>
    </div>
  );
};

export default WaitingBase;
