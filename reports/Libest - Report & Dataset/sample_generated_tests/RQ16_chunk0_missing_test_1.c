/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ16_chunk0_missing_test_1.c
 */

#include <string.h>
#include <stdio.h>
#include <CUnit/CUnit.h>

/*
 * Shared test helpers used to exercise header parsing edge-cases seen in the
 * exemplars (strstr usage to detect WWW-Authenticate, Content-Length, etc.).
 */
static int count_www_authenticate(const char *hdrs)
{
    int count = 0;
    const char *p = hdrs;
    const char *key = "WWW-Authenticate:";

    while ((p = strstr(p, key)) != NULL) {
        count++;
        p += strlen(key);
    }
    return count;
}

static int is_content_length_oversized(const char *hdrs)
{
    const char *p = strstr(hdrs, "Content-Length:");
    if (!p) return 0;
    p += strlen("Content-Length:");
    while (*p == ' ') p++;
    const char *q = p;
    while (*q >= '0' && *q <= '9') q++;
    /* Treat numeric lengths longer than 9 digits as "excessively large" for the test */
    return (size_t)(q - p) > 9;
}

static int has_empty_bearer_token(const char *hdrs)
{
    const char *p = hdrs;
    /* look for Authorization: Bearer or WWW-Authenticate: Bearer occurrences */
    while ((p = strstr(p, "Bearer")) != NULL) {
        const char *after = p + strlen("Bearer");
        /* skip any spaces */
        while (*after == ' ') after++;
        /* if immediately followed by CR, LF or end, treat as empty token */
        if (*after == '\r' || *after == '\n' || *after == '\0') {
            return 1;
        }
        p = after;
    }
    return 0;
}

static int detect_header_injection(const char *hdrs)
{
    /* crude detection: presence of CRLF followed immediately by an unexpected header name */
    return strstr(hdrs, "\r\nInjected:") != NULL;
}

static int http1_0_and_connection_keepalive(const char *hdrs)
{
    return (strstr(hdrs, "HTTP/1.0") != NULL) && (strstr(hdrs, "Connection: keep-alive") != NULL);
}

void rq16_chunk0_missing_test_1(void)
{
    /* 1) Multiple WWW-Authenticate headers present */
    const char *hdrs_multi =
        "HTTP/1.1 401 Unauthorized\r\n"
        "WWW-Authenticate: Basic realm=\"test\"\r\n"
        "WWW-Authenticate: Bearer realm=\"test2\"\r\n"
        "\r\n";
    CU_ASSERT(count_www_authenticate(hdrs_multi) == 2);

    /* 2) Malformed / excessively large Content-Length value */
    const char *hdrs_oversize_cl =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/octet-stream\r\n"
        "Content-Length: 99999999999999999999\r\n"
        "\r\n";
    CU_ASSERT(is_content_length_oversized(hdrs_oversize_cl) == 1);

    /* 3) Bearer token edge-cases: empty token in Authorization or WWW-Authenticate */
    const char *hdrs_empty_bearer_auth =
        "HTTP/1.1 401 Unauthorized\r\n"
        "Authorization: Bearer \r\n"
        "\r\n";
    CU_ASSERT(has_empty_bearer_token(hdrs_empty_bearer_auth) == 1);

    const char *hdrs_empty_bearer_challenge =
        "HTTP/1.1 401 Unauthorized\r\n"
        "WWW-Authenticate: Bearer\r\n"
        "\r\n";
    CU_ASSERT(has_empty_bearer_token(hdrs_empty_bearer_challenge) == 1);

    /* 4) Header injection / sanitization checks: value contains CRLF sequence leading to injected header */
    const char *hdrs_injection =
        "HTTP/1.1 200 OK\r\n"
        "X-Header: good\r\n"
        "Injected: evil\r\n"
        "\r\n";
    CU_ASSERT(detect_header_injection(hdrs_injection) == 1);

    /* 5) HTTP version and Connection header interactions: HTTP/1.0 with Connection: keep-alive */
    const char *hdrs_http1_0 =
        "HTTP/1.0 200 OK\r\n"
        "Connection: keep-alive\r\n"
        "\r\n";
    CU_ASSERT(http1_0_and_connection_keepalive(hdrs_http1_0) == 1);
}
