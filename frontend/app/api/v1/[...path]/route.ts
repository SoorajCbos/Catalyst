import { NextRequest, NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

function getBackendUrl(): string {
  return (
    process.env.API_BASE_URL ??
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

async function proxyRequest(
  request: NextRequest,
  context: RouteContext
): Promise<NextResponse> {
  try {
    const { path } = await context.params;

    const targetUrl =
      `${getBackendUrl()}/api/v1/${path.join("/")}` +
      request.nextUrl.search;

    // Forward only headers the backend actually needs.
    const headers = new Headers({
      accept: "application/json",
      "accept-encoding": "identity",
    });

    const contentType = request.headers.get("content-type");
    const cookie = request.headers.get("cookie");

    if (contentType) {
      headers.set("content-type", contentType);
    }

    if (cookie) {
      headers.set("cookie", cookie);
    }

    const canHaveBody =
      request.method !== "GET" && request.method !== "HEAD";

    const backendResponse = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: canHaveBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });

    // Buffering avoids compression/streaming mismatches in Slate.
    const body = await backendResponse.arrayBuffer();
    const responseHeaders = new Headers();

    const responseType =
      backendResponse.headers.get("content-type");
    const setCookie =
      backendResponse.headers.get("set-cookie");

    if (responseType) {
      responseHeaders.set("content-type", responseType);
    }

    if (setCookie) {
      responseHeaders.set("set-cookie", setCookie);
    }

    return new NextResponse(body, {
      status: backendResponse.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("API proxy failed:", error);

    return NextResponse.json(
      {
        detail: "The frontend could not reach the backend.",
      },
      {
        status: 502,
      }
    );
  }
}

export function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function OPTIONS(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}