type FeedbackProps = { message: string; error?: boolean };

export function Feedback({ message, error = false }: FeedbackProps) {
  if (!message) return null;
  return <p role={error ? "alert" : "status"}>{message}</p>;
}
