import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  children,
  ...rest
}: ButtonProps) {
  const classes = ["btn", `btn--${variant}`, `btn--${size}`];
  if (className) classes.push(className);
  return (
    <button className={classes.join(" ")} {...rest}>
      {children}
    </button>
  );
}
