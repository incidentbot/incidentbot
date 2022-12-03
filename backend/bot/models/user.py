import logging

from bot.models.pg import Session, TokenBlocklist, User
from typing import Tuple

logger = logging.getLogger(__name__)


def db_user_token_revoke(jti, ttype, user_id, created_at):
    try:
        Session.add(
            TokenBlocklist(
                jti=jti, type=ttype, user_id=user_id, created_at=created_at
            )
        )
        Session.commit()
    except Exception as error:
        logger.error(f"Token revoke created failed for {jti}: {error}")
        Session.rollback()
    finally:
        Session.close()
        Session.remove()


def db_user_lookup(email: str = None, id: int = None, all: bool = False):
    if all:
        try:
            logger.debug(f"Attempting to return all users...")
            user = Session.query(User).order_by(User.id.asc())
            return user
        except Exception as error:
            logger.error(f"User lookup failed: {error}")
        finally:
            Session.close()
            Session.remove()
    elif not all and email != None:
        try:
            logger.debug(f"Attempting to lookup user {email}...")
            user = Session.query(User).filter(User.email == email).first()
            return user
        except Exception as error:
            logger.error(f"User lookup failed for {email}: {error}")
        finally:
            Session.close()
            Session.remove()
    elif not all and id != None:
        try:
            logger.debug(f"Attempting to lookup user id {id}...")
            user = Session.query(User).filter(User.id == id).first()
            return user
        except Exception as error:
            logger.error(f"User lookup failed for {email}: {error}")
        finally:
            Session.close()
            Session.remove()


def db_user_create(
    email: str,
    name: str,
    password: str,
    role: str,
    is_admin: bool = False,
) -> Tuple[bool, str]:
    try:
        if Session.query(User).filter_by(email=email).one_or_none() != None:
            return False, "user_already_exists"
        else:
            new_user = User(
                email=email,
                name=name,
                password=password,
                role=role,
                is_admin=is_admin,
            )
            Session.add(new_user)
            Session.commit()
            return True, "user_created"
    except Exception as error:
        logger.error(f"User creation failed for {email}: {error}")
        Session.rollback()
        return False, error
    finally:
        Session.close()
        Session.remove()


def db_user_delete(email: str) -> Tuple[bool, str]:
    try:
        Session.query(User).filter(User.email == email).delete()
        Session.commit()
        return True, "user_deleted"
    except Exception as error:
        logger.error(f"User deletion failed for {email}: {error}")
        Session.rollback()
        return False, str(error)
    finally:
        Session.close()
        Session.remove()


def db_user_disable(email: str) -> Tuple[bool, str]:
    try:
        user = Session.query(User).filter(User.email == email).one()
        user.is_disabled = True
        Session.commit()
        return True, "user_disabled"
    except Exception as error:
        logger.error(f"User disable failed for {email}: {error}")
        Session.rollback()
        return False, str(error)
    finally:
        Session.close()
        Session.remove()


def db_user_enable(email: str) -> Tuple[bool, str]:
    try:
        user = Session.query(User).filter(User.email == email).one()
        user.is_disabled = False
        Session.commit()
        return True, "user_enabled"
    except Exception as error:
        logger.error(f"User enable failed for {email}: {error}")
        Session.rollback()
        return False, str(error)
    finally:
        Session.close()
        Session.remove()


def db_user_adj_admin(email: str, state: bool) -> Tuple[bool, str]:
    try:
        user = Session.query(User).filter(User.email == email).one()
        user.is_admin = state
        Session.commit()
        return True, "user_edited"
    except Exception as error:
        logger.error(f"User adjust failed for {email}: {error}")
        Session.rollback()
        return False, str(error)
    finally:
        Session.close()
        Session.remove()
