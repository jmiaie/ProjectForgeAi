import express from "express";

const app = express();
const port = Number(process.env.PORT || {{port}});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "{{projectName}}" });
});

app.get("/", (_req, res) => {
  res.json({ message: "Hello from {{projectName}}" });
});

if (process.env.NODE_ENV !== "test") {
  app.listen(port, () => {
    console.log(`{{projectName}} listening on http://localhost:${port}`);
  });
}

export default app;
