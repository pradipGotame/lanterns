/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ16_chunk0_missing_test_2.c
 */

#include <string.h>
#include <assert.h>
#include <stddef.h>

/*
 * Reuse the same simple header-scan callback shown in the exemplar tests.
 */
static int bearer_found = 0;
static size_t curl_data_cb (void *ptr, size_t size, size_t nmemb,
                            void *userdata)
{
    void * rc;

    if (bearer_found == 0) {

        /*
         * WARNING: strstr can be dangerous because it assumes null terminated
         * strings.  In this case the http headers came from EST server and we
         * know they are null terminated
         */
        rc = strstr(ptr, "WWW-Authenticate: Bearer");
        if (rc) {
            bearer_found = 1;
        }
    }

    return size * nmemb;
}

void rq16_chunk0_missing_test_2(void)
{
    /* Multiple WWW-Authenticate headers: Bearer is the second entry */
    const char *hdrs_with_multiple_auth =
        "HTTP/1.1 401 Unauthorized\r\n"
        "WWW-Authenticate: Basic realm=\"test\"\r\n"
        "WWW-Authenticate: Bearer realm=\"example\", error=\"invalid_token\"\r\n"
        "Content-Type: text/plain\r\n\r\n";

    bearer_found = 0;
    /* simulate libcurl delivering the header block to the callback */
    curl_data_cb((void *)hdrs_with_multiple_auth, 1, strlen(hdrs_with_multiple_auth), NULL);
    /* Expect the Bearer challenge to be detected even when it is not the first WWW-Authenticate */
    assert(bearer_found == 1);

    /* Header block without any Bearer challenge should not set the flag */
    const char *hdrs_without_bearer =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: 0\r\n\r\n";

    bearer_found = 0;
    curl_data_cb((void *)hdrs_without_bearer, 1, strlen(hdrs_without_bearer), NULL);
    /* Expect no Bearer detection when none is present */
    assert(bearer_found == 0);
}
