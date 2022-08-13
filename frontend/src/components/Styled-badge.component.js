import { styled } from '@mui/system';
import { Badge } from '@mui/material';

const StyledBadge = styled(Badge)(() => ({
  '& .MuiBadge-badge': {
    right: -25,
    top: 13,
    border: `2px solid primary`,
    padding: '0 4px'
  }
}));

export default StyledBadge;
