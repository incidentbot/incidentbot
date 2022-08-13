import React, { useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton
} from '@mui/material';

import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

export default function DeleteSettingDialog(props) {
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmitDelete = (settingName) => {
    props.handleClickDelete(settingName);
  };

  return (
    <>
      <IconButton
        onClick={handleClickOpen}
        disabled={props.setting.deletable ? false : true}
        aria-label="delete">
        <DeleteForeverIcon color={props.setting.deletable ? 'error' : 'disabled'} />
      </IconButton>
      <Dialog
        open={open}
        onClose={handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description">
        <DialogTitle id="alert-dialog-title">
          {'Are you sure you want to delete this setting?'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            This will delete the setting <b>{props.setting.name}</b> from the database. This action
            is not reversible and this may result in data loss.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            variant="contained"
            color="error"
            onClick={() => handleSubmitDelete(props.setting.name)}>
            Yes
          </Button>
          <Button variant="contained" onClick={handleClose} autoFocus>
            No
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
