FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

uniform vec2 resolution;
uniform float time;
uniform vec3 camera_pos;
uniform vec3 camera_dir;
const int NUM_LIGHTS = 5;

struct Light {
    vec3 position;
    vec3 color;
};

// Define lights
uniform Light lights[NUM_LIGHTS];

// Increase the number of spheres
const int NUM_SPHERES = 4;

struct Sphere {
    vec3 center;
    float radius;
    vec3 color;
    float reflectivity;
    float transparency;
    float ior; // Index of Refraction
    vec3 absorption;
};

struct Plane {
    vec3 point;
    vec3 normal;
    vec3 color;
    float reflectivity;
};

float sphereIntersection(vec3 ro, vec3 rd, Sphere sphere, out vec3 hitNormal) {
    vec3 oc = ro - sphere.center;
    float b = dot(oc, rd);
    float c = dot(oc, oc) - sphere.radius * sphere.radius;
    float h = b * b - c;
    if (h < 0.0) return -1.0;
    float t = -b - sqrt(h);
    if (t > 0.0) {
        hitNormal = normalize((ro + rd * t) - sphere.center);
        return t;
    }
    return -1.0;
}

float planeIntersection(vec3 ro, vec3 rd, Plane plane, out vec3 hitNormal) {
    float denom = dot(rd, plane.normal);
    if (abs(denom) > 0.0001) {
        float t = dot(plane.point - ro, plane.normal) / denom;
        if (t > 0.0) {
            hitNormal = plane.normal;
            return t;
        }
    }
    return -1.0;
}

// Function to compute sky color based on ray direction
vec3 getSkyColor(vec3 rd) {
    // Darker sky gradient
    float t = 0.5 * (rd.y + 1.0);
    vec3 skyColor = mix(vec3(0.4, 0.6, 0.8), vec3(0.0, 0.0, 0.3), t);
    return skyColor;
}

void main() {
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    uv = uv * 2.0 - 1.0;
    uv.x *= resolution.x / resolution.y;

    vec3 ro = camera_pos;
    vec3 rd = normalize(camera_dir + vec3(uv, 0.0));

    // Define spheres
    Sphere spheres[NUM_SPHERES];
    spheres[0] = Sphere(vec3(-1.5, 0.0, 5.0), 1.0, vec3(1.0, 0.0, 0.0), 0.2, 0.0, 1.0, vec3(0.0));
    spheres[1] = Sphere(vec3(1.5, 0.0, 6.0), 1.0, vec3(0.0, 0.0, 1.0), 0.8, 0.0, 1.0, vec3(0.0));
    spheres[2] = Sphere(vec3(0.0, -0.5, 3.0), 0.5, vec3(1.0, 1.0, 1.0), 0.05 , 0.95, 1.3, vec3(0.2));
    spheres[3] = Sphere(vec3(2.0, -0.3, 3.0), 0.7, vec3(1.0, 1.0, 1.0), 0.05, 0.95, 1.5, vec3(0.2));

    // Define plane
    Plane plane = Plane(vec3(0.0, -1.0, 0.0), vec3(0.0, 1.0, 0.0), vec3(0.32, 0.18, 0.26), 0.0);

    vec3 color = vec3(0.0);
    vec3 attenuation = vec3(1.0);
    vec3 ambient = vec3(0.05); // Ambient light
    int maxBounces = 10;

    for (int i = 0; i < maxBounces; i++) {
        float nearestT = -1.0;
        vec3 hitNormal = vec3(0.0);
        vec3 hitColor = vec3(0.0);
        float hitReflectivity = 0.0;
        float hitTransparency = 0.0;
        float hitIOR = 1.0;
        int hitObjectType = -1; // 0 = sphere, 1 = plane
        int hitObjectIndex = -1;

        // Sphere intersections
        for (int j = 0; j < NUM_SPHERES; j++) {
            vec3 n;
            float t = sphereIntersection(ro, rd, spheres[j], n);
            if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
                nearestT = t;
                hitNormal = n;
                hitColor = spheres[j].color;
                hitReflectivity = spheres[j].reflectivity;
                hitTransparency = spheres[j].transparency;
                hitIOR = spheres[j].ior;
                hitObjectType = 0;
                hitObjectIndex = j; // Store the index
            }
        }

        // Plane intersection
        vec3 n;
        float t = planeIntersection(ro, rd, plane, n);
        if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
            nearestT = t;
            hitNormal = n;
            hitColor = plane.color;
            hitReflectivity = plane.reflectivity;
            hitTransparency = 0.0;
            hitIOR = 1.0;
            hitObjectType = 1;
            hitObjectIndex = -1; // No index for plane
        }

        if (nearestT > 0.0) {
            vec3 hitPoint = ro + rd * nearestT;

            // Lighting calculations
            vec3 totalDiffuse = vec3(0.0);
            for (int l = 0; l < NUM_LIGHTS; l++) {
                vec3 lightDir = normalize(lights[l].position - hitPoint);
                float shadow = 1.0;

                // Shadow ray for spheres
                for (int j = 0; j < NUM_SPHERES; j++) {
                    vec3 tempNormal;
                    float tShadow = sphereIntersection(hitPoint + hitNormal * 0.001, lightDir, spheres[j], tempNormal);
                    if (tShadow > 0.0) {
                        shadow = 0.0;
                        break;
                    }
                }

                // Shadow ray for plane
                vec3 tempNormal;
                float tShadowPlane = planeIntersection(hitPoint + hitNormal * 0.001, lightDir, plane, tempNormal);
                if (tShadowPlane > 0.0) {
                    shadow = 0.0;
                }

                // Diffuse lighting
                float diff = max(dot(hitNormal, lightDir), 0.0) * shadow;
                totalDiffuse += diff * lights[l].color;
            }

            vec3 lighting = (totalDiffuse * hitColor) + ambient;
            color += attenuation * lighting;

            if (i < maxBounces - 1) {
                if (hitTransparency > 0.0) {
                    // Refraction with Fresnel effect
                    vec3 n = hitNormal;
                    float cosi = clamp(dot(rd, n), -1.0, 1.0);
                    float etai = 1.0, etat = hitIOR;
                    if (cosi > 0.0) {
                        n = -n;
                        float temp = etai;
                        etai = etat;
                        etat = temp;
                    }
                    float etaRatio = etai / etat;
                    float sint = etaRatio * sqrt(max(0.0, 1.0 - cosi * cosi));

                    float kr;
                    // Total internal reflection
                    if (sint >= 1.0) {
                        kr = 1.0;
                    } else {
                        float cost = sqrt(max(0.0, 1.0 - sint * sint));
                        cosi = abs(cosi);
                        float Rs = ((etat * cosi) - (etai * cost)) / ((etat * cosi) + (etai * cost));
                        float Rp = ((etai * cosi) - (etat * cost)) / ((etai * cosi) + (etat * cost));
                        kr = (Rs * Rs + Rp * Rp) / 2.0;
                    }

                    if (kr < 1.0) {
                        // Refraction
                        vec3 refractedDir = refract(rd, n, etaRatio);
                        ro = hitPoint + refractedDir * 0.001;
                        rd = refractedDir;

                        // Calculate the distance traveled in the medium
                        float distanceInMedium = nearestT;

                        // Apply Beer–Lambert Law
                        vec3 absorption = vec3(0.0);
                        if (hitObjectType == 0 && hitObjectIndex >= 0) {
                            absorption = spheres[hitObjectIndex].absorption;
                        }
                        attenuation *= exp(-absorption * distanceInMedium);

                        attenuation *= (1.0 - kr) * hitColor * hitTransparency;
                    } else {
                        // Total internal reflection
                        vec3 reflectedDir = reflect(rd, n);
                        ro = hitPoint + reflectedDir * 0.001;
                        rd = reflectedDir;
                        attenuation *= kr * hitColor * hitTransparency;
                    }
                } else if (hitReflectivity > 0.0) {
                    // Reflection
                    attenuation *= hitReflectivity;
                    ro = hitPoint + hitNormal * 0.001;
                    rd = reflect(rd, hitNormal);
                } else {
                    break;
                }
            } else {
                break;
            }
        } else {
            // Background (sky) color
            vec3 skyColor = getSkyColor(rd);
            color += attenuation * skyColor;
            break;
        }
    }

    FragColor = vec4(color, 1.0);
}
"""