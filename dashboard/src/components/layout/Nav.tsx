import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import styles from './Nav.module.css';

const navItems = [
  { to: '/', label: 'Overview' },
  { to: '/intelligence', label: 'Intelligence' },
  { to: '/strategies', label: 'Strategies' },
  { to: '/reflections', label: 'Reflections' },
  { to: '/dreams', label: 'Dreams' },
];

export default function Nav() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className={`${styles.nav} glassmorphism`}>
      <div className={styles.logo}>MNEMOX</div>
      <button
        className={styles.hamburger}
        onClick={() => setIsMenuOpen((v) => !v)}
        aria-label="Toggle navigation"
      >
        <span className={`${styles.hamburgerLine} ${isMenuOpen ? styles.hamburgerOpen : ''}`} />
        <span className={`${styles.hamburgerLine} ${isMenuOpen ? styles.hamburgerOpen : ''}`} />
        <span className={`${styles.hamburgerLine} ${isMenuOpen ? styles.hamburgerOpen : ''}`} />
      </button>
      <div className={`${styles.links} ${isMenuOpen ? styles.linksOpen : ''}`}>
        {navItems.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.linkActive : ''}`
            }
            onClick={() => setIsMenuOpen(false)}
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
