import { useSpring, animated, easings } from 'react-spring';
import logo from '../img/logo.png';

const AnimatedAppLogo = (props) => {
  const { scale } = useSpring({
    from: {
      scale: 1.0
    },
    to: {
      scale: 1.2
    },
    config: {
      duration: props.duration,
      easing: easings.easeInOutQuart
    },
    loop: { reverse: true }
  });

  return (
    <animated.div
      style={{
        width: props.width,
        height: props.height,
        borderRadius: props.borderRadius,
        scale
      }}>
      <img alt="Incident Bot" width={props.width} height={props.height} src={logo} />
    </animated.div>
  );
};

AnimatedAppLogo.defaultProps = { width: 60, height: 60, borderRadius: 35, duration: 4000 };

export default AnimatedAppLogo;
